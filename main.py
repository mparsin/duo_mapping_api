from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db, Category, Lines, ERPTable, ERPColumn, SubCategory, TableSet, GitHubConnection
from auth import require_cognito_token
from schemas import (
    Category as CategorySchema,
    Lines as LinesSchema,
    ERPTable as ERPTableSchema,
    ERPColumn as ERPColumnSchema,
    ERPColumnCommentResponse,
    LineCreateRequest,
    LineUpdate,
    LineResponse,
    SubCategory as SubCategorySchema,
    SubCategoryUpdate,
    ColumnSearchResult,
    CategoryMappingInfo,
    TableMatchRequest,
    TableMatchResult,
    CategoryConfigUpdate,
    CategoryConfigResponse,
    TableSet as TableSetSchema,
    GitHubConnectionSetRequest,
    GitHubConnectionStatusResponse,
    CreateSchemaPRRequest,
    CreateSchemaPRResponse,
)
from typing import List, Dict, Any, Optional
from sqlalchemy import func
import json
import hashlib
import os
import base64
from datetime import datetime
from cryptography.fernet import Fernet
import httpx

# OpenAPI documentation configuration
app = FastAPI(
    title="Duo Mapping API",
    version="1.0.0",
    description="""
    ## Duo Mapping API

    A comprehensive API for managing ERP table and column mappings for data transformation workflows.
    
    ### Features
    
    * **Category Management**: Organize mappings by categories and sub-categories
    * **Line Mappings**: Map data fields to ERP tables and columns
    * **Table & Column Search**: Search and discover ERP schema elements
    * **Schema Generation**: Export mapped schemas for implementation
    * **Progress Tracking**: Monitor mapping completion percentages
    
    ### API Organization
    
    All endpoints are prefixed with `/api` and organized by functional area:
    
    * **Categories**: Manage mapping categories and sub-categories
    * **Lines**: Handle individual field mappings
    * **Tables & Columns**: ERP schema discovery and search
    * **Schema Export**: Generate implementation-ready schemas
    * **Utilities**: Health checks and maintenance operations
    """,
    contact={
        "name": "API Support",
        "email": "support@redzone.com",
    },
    license_info={
        "name": "Private",
    },
    openapi_tags=[
        {
            "name": "Root",
            "description": "Basic API information and health checks"
        },
        {
            "name": "Categories", 
            "description": "Operations for managing mapping categories and their completion tracking"
        },
        {
            "name": "Sub-Categories",
            "description": "Operations for managing category subdivisions and their metadata"
        },
        {
            "name": "Lines",
            "description": "Operations for managing individual field mappings to ERP tables and columns"
        },
        {
            "name": "Tables",
            "description": "Operations for discovering and working with ERP table structures"
        },
        {
            "name": "Columns", 
            "description": "Operations for searching and working with ERP column definitions"
        },
        {
            "name": "Search",
            "description": "Advanced search operations for finding optimal table and column matches"
        },
        {
            "name": "Schema Export",
            "description": "Operations for generating and downloading implementation-ready schemas"
        },
        {
            "name": "Utilities",
            "description": "System maintenance and health monitoring operations"
        }
    ]
)

# CORS: dev = http://localhost:4200, prod = SPA origin (e.g. CloudFront or S3 website URL)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:4200").strip().split(",")
_cors_origins = [o.strip() for o in _cors_origins if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins if _cors_origins else ["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Create API router with /api prefix; all routes require valid Cognito access token
from fastapi import APIRouter
api_router = APIRouter(prefix="/api", dependencies=[Depends(require_cognito_token)])

# Helper function to calculate and update percent_mapped for a category
def update_category_percent_mapped(db: Session, category_id: int):
    """Calculate and update the percent_mapped field for a category"""
    # Get total lines count for this category (exclude lines only if field_name is NULL AND both table_id and column_id are NULL AND not excluded)
    total_lines = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        ~(
            (Lines.field_name.is_(None) | (Lines.field_name == "")) &
            Lines.table_id.is_(None) &
            Lines.column_id.is_(None)
        ),
        Lines.exclude == False
    ).scalar()
    
    # Get total lines count for this category (all lines except those with NULL field_name AND both table_id and column_id NULL, regardless of exclude status)
    total_lines_all = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        ~(
            (Lines.field_name.is_(None) | (Lines.field_name == "")) &
            Lines.table_id.is_(None) &
            Lines.column_id.is_(None)
        )
    ).scalar()
    
    # Count excluded lines (including those with NULL field_name that are excluded)
    excluded_lines = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        Lines.exclude == True
    ).scalar()
    
    # Get total lines in category (all lines, regardless of field_name or exclude status)
    total_lines_in_category = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id
    ).scalar()
    
    if total_lines_in_category == 0:
        # No lines in category at all, set percent to 0
        percent_mapped = 0.0
    elif total_lines == 0 and excluded_lines > 0:
        # All valid lines in category are excluded, set percent to 100 (task completed)
        percent_mapped = 100.0
    else:
        # Count mapped lines (lines that have both table_id and column_id AND exclude=False)
        # Note: field_name can be NULL as long as table_id and column_id are not NULL
        mapped_lines = db.query(func.count(Lines.id)).filter(
            Lines.categoryid == category_id,
            Lines.table_id.isnot(None),
            Lines.column_id.isnot(None),
            Lines.exclude == False
        ).scalar()
        
        # Calculate percentage
        percent_mapped = (mapped_lines / total_lines) * 100.0
    
    # Update the category's percent_mapped field
    db.query(Category).filter(Category.id == category_id).update({
        Category.percent_mapped: percent_mapped
    })
    db.commit()

# Helper function to calculate SHA-256 hash of schema content
def calculate_schema_hash(tables: List[Dict]) -> str:
    """
    Calculate SHA-256 hash of the schema tables array.
    Uses deterministic JSON serialization (sorted keys, no whitespace) to ensure
    the same schema content always produces the same hash.
    """
    # Sort tables by name for consistency
    sorted_tables = sorted(tables, key=lambda x: x["name"])
    # Serialize with sorted keys, no whitespace for deterministic output
    schema_json = json.dumps(sorted_tables, sort_keys=True, separators=(',', ':'))
    # Calculate SHA-256 hash
    return hashlib.sha256(schema_json.encode('utf-8')).hexdigest()

# Helper function to generate schema JSON for mapped tables and columns
def generate_mapped_schema(db: Session) -> Dict[str, Any]:
    """Generate schema JSON containing only tables and columns that have mappings"""
    
    # Get all mapped lines (lines that have both table_id and column_id and exclude=False)
    mapped_lines = db.query(Lines).filter(
        Lines.table_id.isnot(None),
        Lines.column_id.isnot(None),
        Lines.exclude == False
    ).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column),
        joinedload(Lines.category),
        joinedload(Lines.sub_category)
    ).all()
    
    # Group mapped columns by table
    tables_dict = {}
    
    for line in mapped_lines:
        table = line.erp_table
        column = line.erp_column
        
        if not table or not column:
            continue
            
        table_name = table.name
        
        # Initialize table entry if not exists
        if table_name not in tables_dict:
            tables_dict[table_name] = {
                "name": table_name,
                "description": table.description or f"Table {table_name}",
                "columns": {}
            }
        
        # Add column if not already added (avoid duplicates)
        column_name = column.name
        if column_name not in tables_dict[table_name]["columns"]:
            # Create column entry with available data including constraints
            column_entry = {
                "name": column_name,
                "type": column.type or "unknown",
                "constraints": {
                    "not_null": column.not_null if column.not_null is not None else False,
                    "primary_key": column.primary_key if column.primary_key is not None else False,
                    "unique": column.unique if column.unique is not None else False,
                    "default": column.default
                },
                "comment": column.comment,
                "category": line.category.Name if line.category else None,
                "sub_category": line.sub_category.name if line.sub_category else None,
                "group": line.category.tab if line.category else None,
                "epic": line.category.epic if line.category else None,
                "isaiload": line.category.isaiload if line.category else None,
                "iskeyfield": line.iskeyfield,
                "isfkfield": line.isfkfield
            }
            
            # Add description field if reason is not null
            if line.reason is not None and line.reason.strip():
                column_entry["description"] = line.reason
            
            tables_dict[table_name]["columns"][column_name] = column_entry
    
    # Convert to final format (list of tables with columns as list)
    tables_list = []
    for table_data in tables_dict.values():
        # Sort columns by name for deterministic hash calculation
        columns_list = list(table_data["columns"].values())
        columns_list.sort(key=lambda x: x["name"])
        table_entry = {
            "name": table_data["name"],
            "description": table_data["description"],
            "columns": columns_list
        }
        tables_list.append(table_entry)
    
    # Sort tables by name for consistent output
    tables_list.sort(key=lambda x: x["name"])
    
    # Calculate schema version hash (only on actual schema content, excluding metadata)
    schema_version = calculate_schema_hash(tables_list)
    
    return {
        "tables": tables_list,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_tables": len(tables_list),
        "total_mapped_columns": sum(len(table["columns"]) for table in tables_list),
        "schema_version": schema_version
    }

# Helper function to generate upload config JSON from category table
def generate_upload_config(db: Session) -> Dict[str, Any]:
    """Generate upload config JSON from category table grouped by table sets (ordered by table_set id), with tables ordered by category line_no"""
    
    # Get all categories with both config and table_set_id, ordered by seq_no (line_no)
    categories = db.query(Category).filter(
        Category.config.isnot(None),  # Only categories with config
        Category.table_set_id.isnot(None)  # Only categories assigned to a table set
    ).options(
        joinedload(Category.table_set)  # Eagerly load table_set relationship
    ).order_by(Category.seq_no.nulls_last(), Category.id).all()
    
    # Group categories by table_set_id
    table_set_groups = {}
    
    for category in categories:
        # Skip if table_set is not loaded (shouldn't happen with filter above)
        if not category.table_set:
            continue
        
        table_set_id = category.table_set_id
        
        # Initialize group if not exists
        if table_set_id not in table_set_groups:
            table_set_groups[table_set_id] = {
                "table_set_id": table_set_id,
                "set_name": category.table_set.name,
                "tables": []
            }
        
        # Parse the config JSON to get table configuration
        config = category.config
        
        # Ensure config is a dictionary
        if not isinstance(config, dict):
            # Skip categories with invalid config
            continue
        
        # Create the table entry from config with line_no for sorting
        table_entry = {
            "table": config.get("table", " *** UNKNOWN *** "),
            "batch_size": config.get("batch_size", 1),
            "endpoint": config.get("endpoint", " *** UNKNOWN *** "),
            "related_tables": config.get("related_tables", None),
            "line_no": category.line_no if category.line_no is not None else float('inf')  # For sorting
        }
        
        # Add table to this set's tables list
        table_set_groups[table_set_id]["tables"].append(table_entry)
    
    # Convert to list and sort by table_set_id
    upload_order = []
    for table_set_data in sorted(table_set_groups.values(), key=lambda x: x["table_set_id"]):
        # Sort tables within this set by line_no
        sorted_tables = sorted(table_set_data["tables"], key=lambda t: t["line_no"])
        
        # Remove line_no from final output (it was only needed for sorting)
        final_tables = []
        for table in sorted_tables:
            final_table = {
                "table": table["table"],
                "batch_size": table["batch_size"],
                "endpoint": table["endpoint"],
                "related_tables": table["related_tables"]
            }
            final_tables.append(final_table)
        
        set_entry = {
            "set_name": table_set_data["set_name"],
            "tables": final_tables
        }
        upload_order.append(set_entry)
    
    return {
        "upload_order": upload_order,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_sets": len(upload_order)
    }

@app.get(
    "/",
    tags=["Root"],
    summary="API Root Endpoint",
    description="Returns basic API status and welcome message",
    responses={
        200: {
            "description": "API is running successfully",
            "content": {
                "application/json": {
                    "example": {"message": "Duo Mapping API is running"}
                }
            }
        }
    },
)
async def root():
    """
    **Welcome endpoint for the Duo Mapping API**
    
    This endpoint provides a simple health check and confirms the API is operational.
    Use this to verify the service is running before making other API calls.
    """
    return {"message": "Duo Mapping API is running"}


@app.get(
    "/api/health",
    tags=["Utilities"],
    summary="Health Check",
    description="Simple health check to verify API availability (no auth required)",
    responses={
        200: {
            "description": "API is healthy and operational",
            "content": {
                "application/json": {
                    "example": {"status": "healthy"}
                }
            }
        }
    },
)
async def health_check():
    """
    **API health check**

    Simple endpoint to verify the API is running and operational.
    Use this for monitoring and load balancer health checks.
    No authentication required.
    """
    return {"status": "healthy"}


# API endpoints with /api prefix
@api_router.get(
    "/categories",
    response_model=List[CategorySchema],
    tags=["Categories"],
    summary="Get All Categories",
    description="Retrieve all mapping categories with their completion percentages",
    responses={
        200: {
            "description": "List of categories successfully retrieved",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "Name": "Customer Data",
                            "percent_mapped": 75.5,
                            "tab": "customers",
                            "seq_no": 1,
                            "epic": "Data Migration",
                            "isaiload": False
                        }
                    ]
                }
            }
        }
    }
)
async def get_categories(db: Session = Depends(get_db)):
    """
    **Retrieve all mapping categories**
    
    Returns a list of all categories ordered by sequence number, including:
    - Category ID and name
    - Mapping completion percentage
    - Associated tab and epic information
    - Sequence ordering
    """
    categories = db.query(Category).order_by(Category.seq_no).all()
    return categories

@api_router.get(
    "/categories/{category_id}",
    response_model=CategorySchema,
    tags=["Categories"],
    summary="Get Category by ID",
    description="Retrieve a specific category by its unique identifier",
    responses={
        200: {
            "description": "Category successfully retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "Name": "Customer Data",
                        "percent_mapped": 75.5,
                        "tab": "customers",
                        "seq_no": 1,
                        "epic": "Data Migration",
                        "isaiload": False
                    }
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        }
    }
)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """
    **Retrieve a specific category**
    
    Get detailed information about a single category including its mapping progress.
    
    - **category_id**: Unique identifier for the category
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@api_router.patch(
    "/categories/{category_id}/config",
    response_model=CategoryConfigResponse,
    tags=["Categories"],
    summary="Update Category Config",
    description="Update the configuration settings for a specific category",
    responses={
        200: {
            "description": "Category config successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "Name": "Customer Data",
                        "config": {"theme": "blue", "enabled": True, "settings": {"auto_save": True}},
                        "isaiload": False,
                        "message": "Config successfully updated"
                    }
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        },
        500: {
            "description": "Database validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Database validation failed: Invalid JSON structure"}
                }
            }
        }
    }
)
async def update_category_config(
    category_id: int,
    config_data: CategoryConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    **Update category configuration**
    
    Updates the configuration settings for an existing category. The config field
    accepts any valid JSON object that can be stored in PostgreSQL.
    
    - **category_id**: Unique identifier for the category
    - **config_data**: Object containing the new configuration settings
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    try:
        # Update the config field
        category.config = config_data.config
        db.commit()
        db.refresh(category)
        
        return CategoryConfigResponse(
            id=category.id,
            Name=category.Name,
            config=category.config,
            isaiload=category.isaiload,
            message="Config successfully updated"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database validation failed: {str(e)}")

@api_router.post(
    "/categories/{category_id}/config",
    response_model=CategoryConfigResponse,
    tags=["Categories"],
    summary="Create Category Config",
    description="Add configuration settings to a category that doesn't have any config yet",
    responses={
        200: {
            "description": "Category config successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "Name": "Customer Data",
                        "config": {"theme": "blue", "enabled": True, "settings": {"auto_save": True}},
                        "isaiload": False,
                        "message": "Config successfully created"
                    }
                }
            }
        },
        400: {
            "description": "Category already has config",
            "content": {
                "application/json": {
                    "example": {"detail": "Category already has configuration settings. Use PATCH to update."}
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        },
        500: {
            "description": "Database validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Database validation failed: Invalid JSON structure"}
                }
            }
        }
    }
)
async def create_category_config(
    category_id: int,
    config_data: CategoryConfigUpdate,
    db: Session = Depends(get_db)
):
    """
    **Create category configuration**
    
    Adds configuration settings to a category that doesn't have any config yet.
    If the category already has config, returns an error suggesting to use PATCH instead.
    
    - **category_id**: Unique identifier for the category
    - **config_data**: Object containing the configuration settings to add
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category already has config
    if category.config is not None:
        raise HTTPException(
            status_code=400, 
            detail="Category already has configuration settings. Use PATCH to update."
        )
    
    try:
        # Add the config field
        category.config = config_data.config
        db.commit()
        db.refresh(category)
        
        return CategoryConfigResponse(
            id=category.id,
            Name=category.Name,
            config=category.config,
            isaiload=category.isaiload,
            message="Config successfully created"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database validation failed: {str(e)}")

@api_router.delete(
    "/categories/{category_id}/config",
    response_model=CategoryConfigResponse,
    tags=["Categories"],
    summary="Delete Category Config",
    description="Remove configuration settings from a category",
    responses={
        200: {
            "description": "Category config successfully deleted",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "Name": "Customer Data",
                        "config": None,
                        "message": "Config successfully deleted"
                    }
                }
            }
        },
        404: {
            "description": "Category not found or has no config",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found or has no configuration to delete"}
                }
            }
        }
    }
)
async def delete_category_config(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    **Delete category configuration**
    
    Removes the configuration settings from a category by setting the config field to null.
    
    - **category_id**: Unique identifier for the category
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if category has config to delete
    if category.config is None:
        raise HTTPException(
            status_code=404, 
            detail="Category not found or has no configuration to delete"
        )
    
    # Remove the config field
    category.config = None
    db.commit()
    db.refresh(category)
    
    return CategoryConfigResponse(
        id=category.id,
        Name=category.Name,
        config=category.config,
        isaiload=category.isaiload,
        message="Config successfully deleted"
    )

@api_router.get(
    "/categories/{category_id}/sub-categories",
    response_model=List[SubCategorySchema],
    tags=["Sub-Categories"],
    summary="Get Sub-Categories by Category",
    description="Retrieve all sub-categories for a specific category",
    responses={
        200: {
            "description": "Sub-categories successfully retrieved",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Personal Information",
                            "category_id": 1,
                            "comment": "Customer personal details",
                            "seq_no": 1
                        }
                    ]
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        }
    }
)
async def get_sub_categories_by_category(category_id: int, db: Session = Depends(get_db)):
    """
    **Get all sub-categories for a category**
    
    Returns sub-categories ordered by sequence number (nulls last), then by ID.
    
    - **category_id**: Unique identifier for the parent category
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Query sub-categories for the category ordered by seq_no (nulls last), then by ID
    sub_categories = db.query(SubCategory).filter(
        SubCategory.category_id == category_id
    ).order_by(SubCategory.seq_no.nulls_last(), SubCategory.id).all()
    return sub_categories

@api_router.get(
    "/categories/{category_id}/sub-categories/{sub_category_id}",
    response_model=SubCategorySchema,
    tags=["Sub-Categories"],
    summary="Get Sub-Category by ID",
    description="Retrieve a specific sub-category within a category",
    responses={
        200: {
            "description": "Sub-category successfully retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Personal Information",
                        "category_id": 1,
                        "comment": "Customer personal details",
                        "seq_no": 1
                    }
                }
            }
        },
        404: {
            "description": "Category or sub-category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Sub-category not found"}
                }
            }
        }
    }
)
async def get_sub_category(category_id: int, sub_category_id: int, db: Session = Depends(get_db)):
    """
    **Get a specific sub-category**
    
    Retrieve detailed information about a single sub-category within its parent category.
    
    - **category_id**: Unique identifier for the parent category
    - **sub_category_id**: Unique identifier for the sub-category
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Query the specific sub-category
    sub_category = db.query(SubCategory).filter(
        SubCategory.id == sub_category_id,
        SubCategory.category_id == category_id
    ).first()
    
    if not sub_category:
        raise HTTPException(status_code=404, detail="Sub-category not found")
    
    return sub_category

@api_router.patch(
    "/categories/{category_id}/sub-categories/{sub_category_id}",
    response_model=SubCategorySchema,
    tags=["Sub-Categories"],
    summary="Update Sub-Category Comment",
    description="Update the comment field of a sub-category (name is not editable)",
    responses={
        200: {
            "description": "Sub-category successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Personal Information",
                        "category_id": 1,
                        "comment": "Updated customer personal details",
                        "seq_no": 1
                    }
                }
            }
        },
        404: {
            "description": "Category or sub-category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Sub-category not found"}
                }
            }
        }
    }
)
async def update_sub_category_comment(
    category_id: int,
    sub_category_id: int,
    sub_category_data: SubCategoryUpdate,
    db: Session = Depends(get_db)
):
    """
    **Update sub-category comment**
    
    Updates only the comment field of a sub-category. The name field is read-only.
    
    - **category_id**: Unique identifier for the parent category
    - **sub_category_id**: Unique identifier for the sub-category
    - **sub_category_data**: Object containing the comment to update
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if sub-category exists
    existing_sub_category = db.query(SubCategory).filter(
        SubCategory.id == sub_category_id,
        SubCategory.category_id == category_id
    ).first()
    
    if not existing_sub_category:
        raise HTTPException(status_code=404, detail="Sub-category not found")
    
    # Update the comment field only
    if sub_category_data.comment is not None:
        existing_sub_category.comment = sub_category_data.comment
    
    db.commit()
    db.refresh(existing_sub_category)
    return existing_sub_category

@api_router.patch(
    "/categories/{category_id}/sub-categories/{sub_category_id}/exclude",
    tags=["Sub-Categories"],
    summary="Exclude Entire Sub-Category",
    description="Exclude all lines in a sub-category from percentage calculations",
    responses={
        200: {
            "description": "Sub-category lines successfully excluded",
            "content": {
                "application/json": {
                    "example": {
                        "category_id": 1,
                        "category_name": "Customer Data",
                        "sub_category_id": 1,
                        "sub_category_name": "Personal Information",
                        "lines_updated": 8,
                        "exclude_status": True,
                        "message": "Successfully excluded 8 lines from sub-category 'Personal Information'"
                    }
                }
            }
        },
        404: {
            "description": "Category or sub-category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Sub-category not found"}
                }
            }
        }
    }
)
async def exclude_sub_category(category_id: int, sub_category_id: int, db: Session = Depends(get_db)):
    """
    **Exclude entire sub-category from percentage calculations**
    
    Sets exclude=True for all lines in the specified sub-category. This will
    remove all lines in the sub-category from mapping completion percentage calculations.
    
    - **category_id**: Unique identifier for the parent category
    - **sub_category_id**: Unique identifier for the sub-category to exclude
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if sub-category exists
    sub_category = db.query(SubCategory).filter(
        SubCategory.id == sub_category_id,
        SubCategory.category_id == category_id
    ).first()
    
    if not sub_category:
        raise HTTPException(status_code=404, detail="Sub-category not found")
    
    # Update all lines in the sub-category to exclude=True
    lines_updated = db.query(Lines).filter(
        Lines.sub_category_id == sub_category_id
    ).update({
        Lines.exclude: True
    })
    
    db.commit()
    
    # Update percent_mapped for the category
    update_category_percent_mapped(db, category_id)
    
    return {
        "category_id": category_id,
        "category_name": category.Name,
        "sub_category_id": sub_category_id,
        "sub_category_name": sub_category.name,
        "lines_updated": lines_updated,
        "exclude_status": True,
        "message": f"Successfully excluded {lines_updated} lines from sub-category '{sub_category.name}'"
    }

@api_router.patch(
    "/categories/{category_id}/sub-categories/{sub_category_id}/include",
    tags=["Sub-Categories"],
    summary="Include Entire Sub-Category",
    description="Include all lines in a sub-category in percentage calculations",
    responses={
        200: {
            "description": "Sub-category lines successfully included",
            "content": {
                "application/json": {
                    "example": {
                        "category_id": 1,
                        "category_name": "Customer Data",
                        "sub_category_id": 1,
                        "sub_category_name": "Personal Information",
                        "lines_updated": 8,
                        "exclude_status": False,
                        "message": "Successfully included 8 lines from sub-category 'Personal Information'"
                    }
                }
            }
        },
        404: {
            "description": "Category or sub-category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Sub-category not found"}
                }
            }
        }
    }
)
async def include_sub_category(category_id: int, sub_category_id: int, db: Session = Depends(get_db)):
    """
    **Include entire sub-category in percentage calculations**
    
    Sets exclude=False for all lines in the specified sub-category. This will
    include all lines in the sub-category in mapping completion percentage calculations.
    
    - **category_id**: Unique identifier for the parent category
    - **sub_category_id**: Unique identifier for the sub-category to include
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if sub-category exists
    sub_category = db.query(SubCategory).filter(
        SubCategory.id == sub_category_id,
        SubCategory.category_id == category_id
    ).first()
    
    if not sub_category:
        raise HTTPException(status_code=404, detail="Sub-category not found")
    
    # Update all lines in the sub-category to exclude=False
    lines_updated = db.query(Lines).filter(
        Lines.sub_category_id == sub_category_id
    ).update({
        Lines.exclude: False
    })
    
    db.commit()
    
    # Update percent_mapped for the category
    update_category_percent_mapped(db, category_id)
    
    return {
        "category_id": category_id,
        "category_name": category.Name,
        "sub_category_id": sub_category_id,
        "sub_category_name": sub_category.name,
        "lines_updated": lines_updated,
        "exclude_status": False,
        "message": f"Successfully included {lines_updated} lines from sub-category '{sub_category.name}'"
    }

@api_router.get(
    "/categories/{category_id}/lines",
    response_model=List[LinesSchema],
    tags=["Lines"],
    summary="Get Lines by Category",
    description="Retrieve all mapping lines for a specific category with table and column information",
    responses={
        200: {
            "description": "Lines successfully retrieved",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "categoryid": 1,
                            "default": "John Doe",
                            "customer_settings": "required",
                            "no_of_chars": "50",
                            "field_name": "customer_name",
                            "reason": "Primary customer identifier",
                            "name": "Customer Name",
                            "comment": "Full customer name",
                            "sub_category_id": 1,
                            "table_id": 5,
                            "column_id": 23,
                            "table_name": "customers",
                            "column_name": "full_name",
                            "exclude": False,
                            "iskeyfield": True,
                            "isfkfield": False
                        }
                    ]
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        }
    }
)
async def get_lines_by_category(category_id: int, db: Session = Depends(get_db)):
    """
    **Get all mapping lines for a category**
    
    Returns all lines (field mappings) for a specific category, including their
    mapped ERP table and column information.
    
    - **category_id**: Unique identifier for the category
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Query lines with joined table and column information ordered by seq_no (nulls last), then by ID
    lines = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.categoryid == category_id).order_by(Lines.seq_no.nulls_last(), Lines.id).all()
    
    # Convert to response format with table_name and column_name
    result = []
    for line in lines:
        line_dict = {
            "id": line.id,
            "categoryid": line.categoryid,
            "default": line.default,
            "customer_settings": line.customer_settings,
            "no_of_chars": line.no_of_chars,
            "field_name": line.field_name,
            "reason": line.reason,
            "name": line.name,
            "comment": line.comment,
            "sub_category_id": line.sub_category_id,
            "table_id": line.table_id,
            "column_id": line.column_id,
            "table_name": line.erp_table.name if line.erp_table else None,
            "column_name": line.erp_column.name if line.erp_column else None,
            "exclude": line.exclude,
            "iskeyfield": line.iskeyfield,
            "isfkfield": line.isfkfield,
            "seq_no": line.seq_no
        }
        result.append(line_dict)
    
    return result


def _line_to_dict(line) -> Dict[str, Any]:
    """Build the same dict shape as list items for a single Lines ORM instance (with erp_table, erp_column loaded)."""
    return {
        "id": line.id,
        "categoryid": line.categoryid,
        "default": line.default,
        "customer_settings": line.customer_settings,
        "no_of_chars": line.no_of_chars,
        "field_name": line.field_name,
        "reason": line.reason,
        "name": line.name,
        "comment": line.comment,
        "sub_category_id": line.sub_category_id,
        "table_id": line.table_id,
        "column_id": line.column_id,
        "table_name": line.erp_table.name if line.erp_table else None,
        "column_name": line.erp_column.name if line.erp_column else None,
        "exclude": line.exclude,
        "iskeyfield": line.iskeyfield,
        "isfkfield": line.isfkfield,
        "seq_no": line.seq_no
    }


@api_router.post(
    "/categories/{category_id}/lines",
    response_model=LinesSchema,
    status_code=201,
    tags=["Lines"],
    summary="Create Line",
    description="Create a new mapping line under a category",
    responses={
        201: {
            "description": "Line successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "categoryid": 1,
                        "name": "Customer Name",
                        "field_name": "customer_name",
                        "sub_category_id": 1,
                        "table_id": 5,
                        "column_id": 23,
                        "table_name": "customers",
                        "column_name": "full_name",
                        "exclude": False,
                        "iskeyfield": False,
                        "isfkfield": False,
                        "seq_no": 1
                    }
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        },
        400: {
            "description": "Invalid sub_category or table/column",
            "content": {
                "application/json": {
                    "example": {"detail": "Sub-category does not belong to this category"}
                }
            }
        }
    }
)
async def create_line(category_id: int, body: LineCreateRequest, db: Session = Depends(get_db)):
    """
    **Create a new mapping line**

    Creates a new line under the given category. Category is taken from the path.
    Optionally assign sub_category, table/column mapping, and other metadata.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if body.sub_category_id is not None:
        sub_cat = db.query(SubCategory).filter(
            SubCategory.id == body.sub_category_id,
            SubCategory.category_id == category_id
        ).first()
        if not sub_cat:
            raise HTTPException(
                status_code=400,
                detail="Sub-category not found or does not belong to this category"
            )

    table_id = body.table_id if (body.table_id and body.table_id != 0) else None
    column_id = body.column_id if (body.column_id and body.column_id != 0) else None

    if table_id is not None:
        table = db.query(ERPTable).filter(ERPTable.id == table_id).first()
        if not table:
            raise HTTPException(status_code=404, detail="ERP table not found")
        if column_id is not None:
            column = db.query(ERPColumn).filter(ERPColumn.id == column_id).first()
            if not column:
                raise HTTPException(status_code=404, detail="ERP column not found")
            if column.table_id != table_id:
                raise HTTPException(status_code=400, detail="Column does not belong to the specified table")

    new_line = Lines(
        categoryid=category_id,
        name=body.name,
        sub_category_id=body.sub_category_id,
        field_name=body.field_name,
        default=body.default,
        reason=body.reason,
        comment=body.comment,
        seq_no=body.seq_no,
        customer_settings=body.customer_settings,
        no_of_chars=body.no_of_chars,
        table_id=table_id,
        column_id=column_id,
        exclude=body.exclude if body.exclude is not None else False,
        iskeyfield=body.iskeyfield if body.iskeyfield is not None else False,
        isfkfield=body.isfkfield if body.isfkfield is not None else False,
    )
    db.add(new_line)
    db.commit()
    db.refresh(new_line)

    update_category_percent_mapped(db, category_id)

    updated_line = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.id == new_line.id).first()

    return _line_to_dict(updated_line)


@api_router.get(
    "/tables",
    response_model=List[ERPTableSchema],
    tags=["Tables"],
    summary="Get All ERP Tables",
    description="Retrieve all available ERP tables in the system",
    responses={
        200: {
            "description": "ERP tables successfully retrieved",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "customers",
                            "description": "Customer master data table"
                        },
                        {
                            "id": 2,
                            "name": "orders",
                            "description": "Sales order transactions"
                        }
                    ]
                }
            }
        }
    }
)
async def get_erp_tables(db: Session = Depends(get_db)):
    """
    **Get all ERP tables**
    
    Returns a complete list of all ERP tables available for mapping.
    These tables represent the target schema for data transformations.
    """
    erp_tables = db.query(ERPTable).all()
    return erp_tables

@api_router.get(
    "/tables/{table_id}/columns",
    response_model=List[ERPColumnSchema],
    tags=["Columns"],
    summary="Get Columns by Table",
    description="Retrieve all columns for a specific ERP table",
    responses={
        200: {
            "description": "Table columns successfully retrieved",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "customer_id",
                            "comment": "Unique customer identifier",
                            "type": "integer",
                            "table_id": 1,
                            "not_null": True,
                            "primary_key": True,
                            "unique": True,
                            "default": None
                        }
                    ]
                }
            }
        },
        404: {
            "description": "ERP table not found",
            "content": {
                "application/json": {
                    "example": {"detail": "ERP table not found"}
                }
            }
        }
    }
)
async def get_erp_columns_by_table(table_id: int, db: Session = Depends(get_db)):
    """
    **Get all columns for an ERP table**
    
    Returns detailed information about all columns in a specific ERP table,
    including data types, constraints, and metadata.
    
    - **table_id**: Unique identifier for the ERP table
    """
    # Check if table exists
    erp_table = db.query(ERPTable).filter(ERPTable.id == table_id).first()
    if not erp_table:
        raise HTTPException(status_code=404, detail="ERP table not found")
    
    columns = db.query(ERPColumn).filter(ERPColumn.table_id == table_id).all()
    return columns


@api_router.get(
    "/column-comment",
    response_model=ERPColumnCommentResponse,
    tags=["Columns"],
    summary="Get ERP column comment",
    description="Return the ERP column comment for a given table name and column name. Lookup is case-insensitive.",
    responses={
        200: {
            "description": "ERP column comment successfully retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "table_name": "customers",
                        "column_name": "full_name",
                        "comment": "Full customer name",
                        "table_id": 5,
                        "column_id": 23
                    }
                }
            }
        },
        400: {
            "description": "Missing or empty table_name or column_name",
            "content": {
                "application/json": {
                    "example": {"detail": "table_name and column_name are required and cannot be empty"}
                }
            }
        },
        404: {
            "description": "ERP column not found",
            "content": {
                "application/json": {
                    "example": {"detail": "ERP column not found"}
                }
            }
        }
    }
)
async def get_erp_column_comment(
    table_name: str,
    column_name: str,
    db: Session = Depends(get_db)
):
    """
    **Get ERP column comment by table name and column name**

    Returns the comment (description) for an ERP column identified by table name and column name.
    Lookup is case-insensitive.

    - **table_name**: ERP table name
    - **column_name**: ERP column name
    """
    if not table_name or not table_name.strip():
        raise HTTPException(
            status_code=400,
            detail="table_name and column_name are required and cannot be empty"
        )
    if not column_name or not column_name.strip():
        raise HTTPException(
            status_code=400,
            detail="table_name and column_name are required and cannot be empty"
        )
    table_key = table_name.strip().lower()
    column_key = column_name.strip().lower()
    row = (
        db.query(ERPColumn, ERPTable)
        .join(ERPTable, ERPColumn.table_id == ERPTable.id)
        .filter(
            func.lower(ERPTable.name) == table_key,
            func.lower(ERPColumn.name) == column_key,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="ERP column not found")
    column, table = row
    return ERPColumnCommentResponse(
        table_name=table.name,
        column_name=column.name,
        comment=column.comment,
        table_id=table.id,
        column_id=column.id,
    )


@api_router.get(
    "/lines/{line_id}",
    response_model=LinesSchema,
    tags=["Lines"],
    summary="Get Line by ID",
    description="Retrieve a single mapping line by ID with table and column information",
    responses={
        200: {
            "description": "Line successfully retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "categoryid": 1,
                        "default": "John Doe",
                        "customer_settings": "required",
                        "no_of_chars": "50",
                        "field_name": "customer_name",
                        "reason": "Primary customer identifier",
                        "name": "Customer Name",
                        "comment": "Full customer name",
                        "sub_category_id": 1,
                        "table_id": 5,
                        "column_id": 23,
                        "table_name": "customers",
                        "column_name": "full_name",
                        "exclude": False,
                        "iskeyfield": True,
                        "isfkfield": False,
                        "seq_no": 1
                    }
                }
            }
        },
        404: {
            "description": "Line not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Line not found"}
                }
            }
        }
    }
)
async def get_line(line_id: int, db: Session = Depends(get_db)):
    """
    **Get a single mapping line**

    Returns one line by ID with ERP table and column names loaded.
    Useful for edit UIs.
    """
    line = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.id == line_id).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")
    return _line_to_dict(line)


@api_router.patch(
    "/lines/{line_id}",
    response_model=LineResponse,
    tags=["Lines"],
    summary="Update Line",
    description="Partially update an existing line (metadata and/or table/column mapping). All request fields are optional.",
    responses={
        200: {
            "description": "Line successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "categoryid": 1,
                        "table_id": 5,
                        "column_id": 23,
                        "table_name": "customers",
                        "column_name": "full_name",
                        "comment": "Updated mapping comment",
                        "exclude": False,
                        "iskeyfield": True,
                        "isfkfield": False,
                        "action": "updated"
                    }
                }
            }
        },
        404: {
            "description": "Line, table, or column not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Line not found"}
                }
            }
        },
        400: {
            "description": "Invalid sub_category or mapping (column doesn't belong to table)",
            "content": {
                "application/json": {
                    "example": {"detail": "Column does not belong to the specified table"}
                }
            }
        }
    }
)
async def update_line(line_id: int, line_data: LineUpdate, db: Session = Depends(get_db)):
    """
    **Update line (partial update)**

    Updates an existing line. Send only the fields you want to change.
    - Metadata: name, field_name, default, reason, comment, seq_no, customer_settings, no_of_chars, sub_category_id
    - Mapping: table_id, column_id (set table_id to 0 or null to clear mapping; column_id to 0 to clear column only)
    - Flags: exclude, iskeyfield, isfkfield

    Validates that sub_category belongs to the line's category and that column belongs to the specified table.
    """
    existing_line = db.query(Lines).filter(Lines.id == line_id).first()
    if not existing_line:
        raise HTTPException(status_code=404, detail="Line not found")

    # Apply metadata fields when provided
    if line_data.name is not None:
        existing_line.name = line_data.name
    if line_data.field_name is not None:
        existing_line.field_name = line_data.field_name
    if line_data.default is not None:
        existing_line.default = line_data.default
    if line_data.reason is not None:
        existing_line.reason = line_data.reason
    if line_data.comment is not None:
        existing_line.comment = line_data.comment
    if line_data.seq_no is not None:
        existing_line.seq_no = line_data.seq_no
    if line_data.customer_settings is not None:
        existing_line.customer_settings = line_data.customer_settings
    if line_data.no_of_chars is not None:
        existing_line.no_of_chars = line_data.no_of_chars

    if line_data.sub_category_id is not None:
        sub_cat = db.query(SubCategory).filter(
            SubCategory.id == line_data.sub_category_id,
            SubCategory.category_id == existing_line.categoryid
        ).first()
        if not sub_cat:
            raise HTTPException(
                status_code=400,
                detail="Sub-category not found or does not belong to this category"
            )
        existing_line.sub_category_id = line_data.sub_category_id

    if line_data.exclude is not None:
        existing_line.exclude = line_data.exclude
    if line_data.iskeyfield is not None:
        existing_line.iskeyfield = line_data.iskeyfield
    if line_data.isfkfield is not None:
        existing_line.isfkfield = line_data.isfkfield

    # Table/column mapping: only when at least one is present in the body
    table_id_sent = line_data.table_id is not None
    column_id_sent = line_data.column_id is not None
    if table_id_sent or column_id_sent:
        if line_data.table_id is None or line_data.table_id == 0:
            existing_line.table_id = None
            existing_line.column_id = None
            db.commit()
            update_category_percent_mapped(db, existing_line.categoryid)
            updated_line = db.query(Lines).options(
                joinedload(Lines.erp_table),
                joinedload(Lines.erp_column)
            ).filter(Lines.id == existing_line.id).first()
            return {
                "id": updated_line.id,
                "categoryid": updated_line.categoryid,
                "table_id": updated_line.table_id,
                "column_id": updated_line.column_id,
                "table_name": updated_line.erp_table.name if updated_line.erp_table else None,
                "column_name": updated_line.erp_column.name if updated_line.erp_column else None,
                "comment": updated_line.comment,
                "exclude": updated_line.exclude,
                "iskeyfield": updated_line.iskeyfield,
                "isfkfield": updated_line.isfkfield,
                "action": "cleared_table_id"
            }

        table = db.query(ERPTable).filter(ERPTable.id == line_data.table_id).first()
        if not table:
            raise HTTPException(status_code=404, detail="ERP table not found")
        existing_line.table_id = line_data.table_id

        if line_data.column_id == 0:
            existing_line.column_id = None
        elif line_data.column_id is not None:
            column = db.query(ERPColumn).filter(ERPColumn.id == line_data.column_id).first()
            if not column:
                raise HTTPException(status_code=404, detail="ERP column not found")
            if column.table_id != line_data.table_id:
                raise HTTPException(status_code=400, detail="Column does not belong to the specified table")
            existing_line.column_id = line_data.column_id
        else:
            existing_line.column_id = None

    db.commit()
    db.refresh(existing_line)
    update_category_percent_mapped(db, existing_line.categoryid)

    updated_line = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.id == existing_line.id).first()

    action = "cleared_column_id" if (column_id_sent and line_data.column_id == 0) else "updated"
    return {
        "id": updated_line.id,
        "categoryid": updated_line.categoryid,
        "table_id": updated_line.table_id,
        "column_id": updated_line.column_id,
        "table_name": updated_line.erp_table.name if updated_line.erp_table else None,
        "column_name": updated_line.erp_column.name if updated_line.erp_column else None,
        "comment": updated_line.comment,
        "exclude": updated_line.exclude,
        "iskeyfield": updated_line.iskeyfield,
        "isfkfield": updated_line.isfkfield,
        "action": action
    }

@api_router.patch(
    "/lines/{line_id}/exclude",
    response_model=LineResponse,
    tags=["Lines"],
    summary="Toggle Line Exclude Status",
    description="Toggle the exclude status of a line (exclude from percentage calculations)",
    responses={
        200: {
            "description": "Line exclude status successfully updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "categoryid": 1,
                        "table_id": 5,
                        "column_id": 23,
                        "table_name": "customers",
                        "column_name": "full_name",
                        "comment": "Mapped to primary customer name field",
                        "exclude": True,
                        "iskeyfield": True,
                        "isfkfield": False,
                        "action": "exclude_toggled"
                    }
                }
            }
        },
        404: {
            "description": "Line not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Line not found"}
                }
            }
        }
    }
)
async def toggle_line_exclude(line_id: int, db: Session = Depends(get_db)):
    """
    **Toggle line exclude status**
    
    Toggles the exclude status of a line. When exclude=True, the line will be
    excluded from all percentage calculations related to mapping.
    
    - **line_id**: Unique identifier for the line to toggle
    """
    # Find the line by ID
    existing_line = db.query(Lines).filter(Lines.id == line_id).first()
    if not existing_line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    # Toggle the exclude status
    existing_line.exclude = not existing_line.exclude
    
    db.commit()
    db.refresh(existing_line)
    
    # Update percent_mapped for the category
    update_category_percent_mapped(db, existing_line.categoryid)
    
    # Load the related table and column data for the response
    updated_line = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.id == existing_line.id).first()
    
    return {
        "id": updated_line.id,
        "categoryid": updated_line.categoryid,
        "table_id": updated_line.table_id,
        "column_id": updated_line.column_id,
        "table_name": updated_line.erp_table.name if updated_line.erp_table else None,
        "column_name": updated_line.erp_column.name if updated_line.erp_column else None,
        "comment": updated_line.comment,
        "exclude": updated_line.exclude,
        "iskeyfield": updated_line.iskeyfield,
        "isfkfield": updated_line.isfkfield,
        "action": "exclude_toggled"
    }

@api_router.patch(
    "/categories/{category_id}/exclude",
    tags=["Categories"],
    summary="Exclude Entire Category",
    description="Exclude all lines in a category from percentage calculations",
    responses={
        200: {
            "description": "Category lines successfully excluded",
            "content": {
                "application/json": {
                    "example": {
                        "category_id": 1,
                        "category_name": "Customer Data",
                        "lines_updated": 15,
                        "exclude_status": True,
                        "message": "Successfully excluded 15 lines from category 'Customer Data'"
                    }
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        }
    }
)
async def exclude_category(category_id: int, db: Session = Depends(get_db)):
    """
    **Exclude entire category from percentage calculations**
    
    Sets exclude=True for all lines in the specified category. This will
    remove all lines in the category from mapping completion percentage calculations.
    
    - **category_id**: Unique identifier for the category to exclude
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update all lines in the category to exclude=True
    lines_updated = db.query(Lines).filter(
        Lines.categoryid == category_id
    ).update({
        Lines.exclude: True
    })
    
    db.commit()
    
    # Update percent_mapped for the category (should be 0% now)
    update_category_percent_mapped(db, category_id)
    
    return {
        "category_id": category_id,
        "category_name": category.Name,
        "lines_updated": lines_updated,
        "exclude_status": True,
        "message": f"Successfully excluded {lines_updated} lines from category '{category.Name}'"
    }

@api_router.patch(
    "/categories/{category_id}/include",
    tags=["Categories"],
    summary="Include Entire Category",
    description="Include all lines in a category in percentage calculations",
    responses={
        200: {
            "description": "Category lines successfully included",
            "content": {
                "application/json": {
                    "example": {
                        "category_id": 1,
                        "category_name": "Customer Data",
                        "lines_updated": 15,
                        "exclude_status": False,
                        "message": "Successfully included 15 lines from category 'Customer Data'"
                    }
                }
            }
        },
        404: {
            "description": "Category not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Category not found"}
                }
            }
        }
    }
)
async def include_category(category_id: int, db: Session = Depends(get_db)):
    """
    **Include entire category in percentage calculations**
    
    Sets exclude=False for all lines in the specified category. This will
    include all lines in the category in mapping completion percentage calculations.
    
    - **category_id**: Unique identifier for the category to include
    """
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Update all lines in the category to exclude=False
    lines_updated = db.query(Lines).filter(
        Lines.categoryid == category_id
    ).update({
        Lines.exclude: False
    })
    
    db.commit()
    
    # Update percent_mapped for the category
    update_category_percent_mapped(db, category_id)
    
    return {
        "category_id": category_id,
        "category_name": category.Name,
        "lines_updated": lines_updated,
        "exclude_status": False,
        "message": f"Successfully included {lines_updated} lines from category '{category.Name}'"
    }

@api_router.get(
    "/search-columns",
    response_model=List[ColumnSearchResult],
    tags=["Search"],
    summary="Search Columns by Name",
    description="Search through all ERP columns by name, returning exact matches first, then partial matches. Includes information about which categories each column is mapped to.",
    responses={
        200: {
            "description": "Column search results with mapping information",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "column_name": "customer_name",
                            "table_name": "customers",
                            "column_id": 23,
                            "table_id": 5,
                            "match_type": "exact",
                            "mapped_categories": [
                                {"id": 1, "name": "Customer Data"},
                                {"id": 2, "name": "Order Management"}
                            ]
                        },
                        {
                            "column_name": "customer_full_name",
                            "table_name": "customer_details",
                            "column_id": 45,
                            "table_id": 12,
                            "match_type": "partial",
                            "mapped_categories": []
                        }
                    ]
                }
            }
        },
        400: {
            "description": "Invalid search parameter",
            "content": {
                "application/json": {
                    "example": {"detail": "columnName parameter is required and cannot be empty"}
                }
            }
        }
    }
)
async def search_columns(columnName: str, db: Session = Depends(get_db)):
    """
    **Search columns by name with mapping information**
    
    Searches through all ERP columns by name, returning results in order of relevance:
    1. Exact matches (case-insensitive)
    2. Partial matches (contains search term)
    
    For each matching column, also returns information about which categories
    the column is mapped to (if any).
    
    - **columnName**: The column name to search for
    """
    if not columnName or not columnName.strip():
        raise HTTPException(status_code=400, detail="columnName parameter is required and cannot be empty")
    
    # Clean the search term
    search_term = columnName.strip().lower()
    
    # Use database-level filtering with ILIKE for case-insensitive search
    # This is much more efficient than loading all data and filtering in Python
    exact_columns = db.query(ERPColumn, ERPTable).join(
        ERPTable, ERPColumn.table_id == ERPTable.id
    ).filter(
        func.lower(ERPColumn.name) == search_term
    ).all()
    
    partial_columns = db.query(ERPColumn, ERPTable).join(
        ERPTable, ERPColumn.table_id == ERPTable.id
    ).filter(
        func.lower(ERPColumn.name).like(f"%{search_term}%"),
        func.lower(ERPColumn.name) != search_term  # Exclude exact matches
    ).all()
    
    # Get all column IDs that matched
    all_matched_column_ids = [col.id for col, _ in exact_columns + partial_columns]
    
    # Single query to get all category mappings for all matched columns
    # This eliminates the N+1 query problem
    category_mappings = {}
    if all_matched_column_ids:
        mappings = db.query(
            Lines.column_id,
            Category.id,
            Category.Name
        ).join(
            Category, Lines.categoryid == Category.id
        ).filter(
            Lines.column_id.in_(all_matched_column_ids)
        ).distinct().all()
        
        # Group mappings by column_id
        for column_id, cat_id, cat_name in mappings:
            if column_id not in category_mappings:
                category_mappings[column_id] = []
            category_mappings[column_id].append(CategoryMappingInfo(id=cat_id, name=cat_name))
    
    # Build results for exact matches
    exact_matches = []
    for column, table in exact_columns:
        exact_matches.append(ColumnSearchResult(
            column_name=column.name,
            table_name=table.name,
            column_id=column.id,
            table_id=table.id,
            match_type="exact",
            mapped_categories=category_mappings.get(column.id, [])
        ))
    
    # Build results for partial matches
    partial_matches = []
    for column, table in partial_columns:
        partial_matches.append(ColumnSearchResult(
            column_name=column.name,
            table_name=table.name,
            column_id=column.id,
            table_id=table.id,
            match_type="partial",
            mapped_categories=category_mappings.get(column.id, [])
        ))
    
    # Return exact matches first, then partial matches
    return exact_matches + partial_matches

@api_router.post(
    "/find-table-matches",
    response_model=List[TableMatchResult],
    tags=["Search"],
    summary="Find Table Matches",
    description="Find tables with the most column matches from a list of column names",
    responses={
        200: {
            "description": "Table match results ordered by match count",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "table_id": 5,
                            "table_name": "customers",
                            "match_count": 3,
                            "matched_columns": ["customer_name", "email", "phone"]
                        },
                        {
                            "table_id": 12,
                            "table_name": "customer_details",
                            "match_count": 2,
                            "matched_columns": ["customer_name", "email"]
                        }
                    ]
                }
            }
        },
        400: {
            "description": "Invalid request data",
            "content": {
                "application/json": {
                    "example": {"detail": "column_names list cannot be empty"}
                }
            }
        }
    }
)
async def find_table_matches(request: TableMatchRequest, db: Session = Depends(get_db)):
    """
    **Find optimal table matches**
    
    Analyzes a list of column names and finds ERP tables with the most matching columns.
    Results are ordered by match count (descending) then by table name (ascending).
    
    This is useful for discovering the best target tables when you have a set of
    source field names that need to be mapped.
    
    - **request**: Object containing the list of column names to match
    """
    if not request.column_names or len(request.column_names) == 0:
        raise HTTPException(status_code=400, detail="column_names list cannot be empty")
    
    # Clean and normalize column names for case-insensitive matching
    search_columns = [col.strip().lower() for col in request.column_names if col.strip()]
    
    if not search_columns:
        raise HTTPException(status_code=400, detail="No valid column names provided")
    
    # Use database-level filtering instead of loading all data
    # This query finds all columns that match any of the search terms
    matching_columns = db.query(
        ERPColumn.name,
        ERPColumn.table_id,
        ERPTable.name.label('table_name')
    ).join(
        ERPTable, ERPColumn.table_id == ERPTable.id
    ).filter(
        func.lower(ERPColumn.name).in_(search_columns)
    ).all()
    
    # Group matches by table
    table_matches_dict = {}
    for column_name, table_id, table_name in matching_columns:
        if table_id not in table_matches_dict:
            table_matches_dict[table_id] = {
                'table_id': table_id,
                'table_name': table_name,
                'matched_columns': [],
                'match_count': 0
            }
        
        table_matches_dict[table_id]['matched_columns'].append(column_name)
        table_matches_dict[table_id]['match_count'] += 1
    
    # Convert to list and sort by match count (descending) then by table name (ascending)
    table_matches = []
    for table_data in table_matches_dict.values():
        table_matches.append(TableMatchResult(
            table_id=table_data['table_id'],
            table_name=table_data['table_name'],
            match_count=table_data['match_count'],
            matched_columns=sorted(table_data['matched_columns'])  # Sort columns for consistency
        ))
    
    # Sort by match count (descending) and then by table name (ascending)
    table_matches.sort(key=lambda x: (-x.match_count, x.table_name))
    
    return table_matches

@api_router.post(
    "/categories/recalculate-percent-mapped",
    tags=["Utilities"],
    summary="Recalculate Mapping Percentages",
    description="Recalculate percent_mapped for all categories based on current line mappings",
    responses={
        200: {
            "description": "Percentages successfully recalculated",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Successfully recalculated percent_mapped for 15 categories",
                        "updated_count": 15
                    }
                }
            }
        }
    }
)
async def recalculate_all_percent_mapped(db: Session = Depends(get_db)):
    """
    **Recalculate mapping completion percentages**
    
    Updates the percent_mapped field for all categories based on their current
    line mappings. This is useful for maintenance after bulk updates or data imports.
    
    The percentage is calculated as:
    (mapped_lines_with_field_name / total_lines_with_field_name) * 100
    """
    categories = db.query(Category).all()
    updated_count = 0
    
    for category in categories:
        update_category_percent_mapped(db, category.id)
        updated_count += 1
    
    return {
        "message": f"Successfully recalculated percent_mapped for {updated_count} categories",
        "updated_count": updated_count
    }

@api_router.get(
    "/download-schema",
    tags=["Schema Export"],
    summary="Download Mapped Schema",
    description="Generate and download a JSON schema file containing only mapped tables and columns",
    responses={
        200: {
            "description": "Schema file successfully generated and downloaded",
            "content": {
                "application/json": {
                    "example": {
                        "tables": [
                            {
                                "name": "customers",
                                "description": "Customer master data table",
                                "columns": [
                                    {
                                        "name": "customer_name",
                                        "type": "varchar",
                                        "constraints": {
                                            "not_null": True,
                                            "primary_key": False,
                                            "unique": False,
                                            "default": None
                                        },
                                        "comment": "Customer full name",
                                        "category": "Customer Data",
                                        "sub_category": "Personal Information",
                                        "description": "Primary customer identifier",
                                        "iskeyfield": True,
                                        "isfkfield": False
                                    }
                                ]
                            }
                        ],
                        "generated_at": "2024-01-15T10:30:00Z",
                        "total_tables": 1,
                        "total_mapped_columns": 1
                    }
                }
            },
            "headers": {
                "Content-Disposition": "attachment; filename=mapped_schema_20240115_103000.json",
                "Content-Type": "application/json"
            }
        },
        500: {
            "description": "Error generating schema",
            "content": {
                "application/json": {
                    "example": {"detail": "Error generating schema: Database connection failed"}
                }
            }
        }
    }
)
async def download_schema(db: Session = Depends(get_db)):
    """
    **Download implementation-ready schema**
    
    Generates and downloads a JSON file containing only tables and columns that
    have active mappings. This schema can be used for implementation and includes:
    
    - Table and column metadata
    - Data type information
    - Constraint details
    - Mapping context (category, sub-category)
    - Custom descriptions from mapping reasons
    
    The file is automatically named with a timestamp for version tracking.
    """
    try:
        # Generate the schema
        schema_data = generate_mapped_schema(db)
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"mapped_schema_{timestamp}.json"
        
        # Return as JSON download
        return JSONResponse(
            content=schema_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/json"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating schema: {str(e)}")

@api_router.get(
    "/download-upload-config",
    tags=["Schema Export"],
    summary="Download Upload Configuration",
    description="Generate and download an upload configuration JSON file grouped by table sets",
    responses={
        200: {
            "description": "Upload config file successfully generated and downloaded",
            "content": {
                "application/json": {
                    "example": {
                        "upload_order": [
                            {
                                "set_name": "Master Data",
                                "tables": [
                                    {
                                        "table": "generalizedCodes",
                                        "batch_size": 1,
                                        "endpoint": "api/bcom/load?entityUri=urn:be:com.qad.base.codes.IGeneralizedCode",
                                        "related_tables": [
                                            {
                                                "table": "connectionGCDomains",
                                                "relation_fields": ["domainCode", "fieldName", "codeValue"],
                                                "parent_fields": ["domainCode", "fieldName", "codeValue"],
                                                "nested_as": "connectionGCDomains"
                                            }
                                        ]
                                    },
                                    {
                                        "table": "users",
                                        "batch_size": 1,
                                        "endpoint": "api/users/load",
                                        "related_tables": None
                                    }
                                ]
                            },
                            {
                                "set_name": "Transactional Data",
                                "tables": [
                                    {
                                        "table": "orders",
                                        "batch_size": 100,
                                        "endpoint": "api/orders/load",
                                        "related_tables": None
                                    }
                                ]
                            }
                        ],
                        "generated_at": "2024-01-15T10:30:00Z",
                        "total_sets": 2
                    }
                }
            },
            "headers": {
                "Content-Disposition": "attachment; filename=upload-config_20240115_103000.json",
                "Content-Type": "application/json"
            }
        },
        500: {
            "description": "Error generating upload config",
            "content": {
                "application/json": {
                    "example": {"detail": "Error generating upload config: Database connection failed"}
                }
            }
        }
    }
)
async def download_upload_config(db: Session = Depends(get_db)):
    """
    **Download upload configuration grouped by table sets**
    
    Generates and downloads a JSON file containing upload configuration based on
    table sets and category configs. Categories are grouped by their assigned table_set,
    and the configuration includes:
    
    - Upload order sets based on table_set names
    - Multiple tables grouped under each set (from categories with the same table_set_id)
    - Table configurations from category config JSON
    - Batch sizes and endpoints for each table
    - Related tables information
    - Sets ordered by table_set id (ascending)
    - Tables within each set ordered by category line_no (ascending)
    
    **Note**: Only categories with both a config and table_set_id will be included.
    Categories without a table_set assignment are excluded.
    
    The file is automatically named with a timestamp for version tracking.
    """
    try:
        # Generate the upload config
        config_data = generate_upload_config(db)
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"upload-config_{timestamp}.json"
        
        # Return as JSON download
        return JSONResponse(
            content=config_data,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/json"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating upload config: {str(e)}")


# --- GitHub connection (encrypted token) and create-schema-pr ---

def _get_fernet():
    """Return Fernet instance from GITHUB_TOKEN_ENCRYPTION_KEY. Key must be 32 url-safe base64 bytes."""
    key = os.getenv("GITHUB_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(
            status_code=503,
            detail="GITHUB_TOKEN_ENCRYPTION_KEY is not set; cannot encrypt or decrypt GitHub token.",
        )
    try:
        if isinstance(key, str):
            key = key.encode("utf-8")
        return Fernet(key)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Invalid GITHUB_TOKEN_ENCRYPTION_KEY: {e}")


def _encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def _decrypt_token(encrypted: str) -> str:
    return _get_fernet().decrypt(encrypted.encode("utf-8")).decode("utf-8")


@api_router.put(
    "/github-connection",
    tags=["Schema Export"],
    summary="Set GitHub connection",
    description="Store a GitHub PAT (encrypted) for use by create-schema-pr. Token is validated with GitHub before storing. One app-wide connection.",
    responses={
        200: {"description": "Connection configured"},
        401: {"description": "Invalid or expired GitHub token"},
        503: {"description": "Encryption key not configured"},
    },
)
async def set_github_connection(
    body: GitHubConnectionSetRequest,
    db: Session = Depends(get_db),
):
    """Set or update the app-wide GitHub connection. Token is encrypted and stored; never returned."""
    # Validate token with GitHub
    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {body.github_token}"},
        )
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired GitHub token.")
    if r.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub API returned {r.status_code}; cannot validate token.",
        )
    encrypted = _encrypt_token(body.github_token)
    row = db.query(GitHubConnection).first()
    if row:
        row.encrypted_token = encrypted
        row.updated_at = datetime.utcnow()
    else:
        db.add(GitHubConnection(encrypted_token=encrypted))
    db.commit()
    return {"status": "configured"}


@api_router.get(
    "/github-connection",
    tags=["Schema Export"],
    summary="GitHub connection status",
    description="Returns whether a GitHub connection is configured. Never returns the token.",
    responses={200: {"description": "Status only"}},
)
async def get_github_connection_status(db: Session = Depends(get_db)):
    row = db.query(GitHubConnection).first()
    return GitHubConnectionStatusResponse(configured=row is not None)


@api_router.delete(
    "/github-connection",
    tags=["Schema Export"],
    summary="Remove GitHub connection",
    description="Deletes the stored GitHub token. create-schema-pr will fail until PUT is called again.",
    responses={200: {"description": "Connection removed"}},
)
async def delete_github_connection(db: Session = Depends(get_db)):
    db.query(GitHubConnection).delete()
    db.commit()
    return {"status": "removed"}


@api_router.post(
    "/create-schema-pr",
    tags=["Schema Export"],
    summary="Create PR with schema",
    description="Generates the mapped schema (same as download-schema), creates a commit on a new branch, and opens a PR. owner, repo, file_path, branch_name, base_branch are read from server .env (GITHUB_SCHEMA_PR_*). GitHub token is from DB (PUT /api/github-connection). Request body: optional author (for visibility), pr_title, pr_body.",
    responses={
        200: {"description": "PR created"},
        412: {"description": "GitHub connection not configured"},
        503: {"description": "Encryption key not set or connection missing"},
    },
)
async def create_schema_pr(
    body: CreateSchemaPRRequest,
    db: Session = Depends(get_db),
):
    """Create a branch and PR with the current mapped schema. Token is loaded from DB (stored via PUT /api/github-connection).
    owner, repo, file_path, branch_name, base_branch are read from server .env."""
    owner = os.getenv("GITHUB_SCHEMA_PR_OWNER")
    repo = os.getenv("GITHUB_SCHEMA_PR_REPO")
    if not owner or not repo:
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: GITHUB_SCHEMA_PR_OWNER and GITHUB_SCHEMA_PR_REPO must be set in .env.",
        )
    file_path = os.getenv("GITHUB_SCHEMA_PR_FILE_PATH", "schema-config.json")
    base_branch = os.getenv("GITHUB_SCHEMA_PR_BASE_BRANCH", "main")
    branch_name = os.getenv("GITHUB_SCHEMA_PR_BRANCH_NAME") or f"schema-export/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    row = db.query(GitHubConnection).first()
    if not row:
        raise HTTPException(
            status_code=412,
            detail="GitHub connection not configured. Use PUT /api/github-connection to set a token.",
        )
    try:
        token = _decrypt_token(row.encrypted_token)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Could not decrypt stored token. Check GITHUB_TOKEN_ENCRYPTION_KEY or re-set the connection.",
        )
    schema_data = generate_mapped_schema(db)
    pr_title = body.pr_title or "Update schema config"
    pr_body = body.pr_body or f"Schema export at {datetime.utcnow().isoformat()}Z"
    if body.author and body.author.strip():
        author_line = f"**Requested by:** {body.author.strip()}\n\n"
        pr_body = author_line + pr_body
        commit_message = f"{pr_title}\n\n(Requested by: {body.author.strip()})"
    else:
        commit_message = pr_title
    content_bytes = json.dumps(schema_data, indent=2).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient() as client:
        # Get base branch SHA
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{base_branch}",
            headers=headers,
        )
        if r.status_code == 401:
            raise HTTPException(
                status_code=401,
                detail="GitHub token expired or revoked. Please update the connection via PUT /api/github-connection.",
            )
        if r.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Repo or branch {base_branch} not found.")
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text or "GitHub API error")
        base_sha = r.json()["object"]["sha"]

        # Create blob
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/blobs",
            headers=headers,
            json={"content": base64.b64encode(content_bytes).decode("utf-8"), "encoding": "base64"},
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text or "Failed to create blob")
        blob_sha = r.json()["sha"]

        # Create tree
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees",
            headers=headers,
            json={
                "base_tree": base_sha,
                "tree": [{"path": file_path, "mode": "100644", "type": "blob", "sha": blob_sha}],
            },
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text or "Failed to create tree")
        tree_sha = r.json()["sha"]

        # Create commit
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/commits",
            headers=headers,
            json={"message": commit_message, "tree": tree_sha, "parents": [base_sha]},
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text or "Failed to create commit")
        commit_sha = r.json()["sha"]

        # Create ref (branch)
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs",
            headers=headers,
            json={"ref": f"refs/heads/{branch_name}", "sha": commit_sha},
        )
        if r.status_code == 422 and "already exists" in (r.text or "").lower():
            raise HTTPException(
                status_code=422,
                detail=f"Branch {branch_name} already exists. Retry later or set GITHUB_SCHEMA_PR_BRANCH_NAME in .env.",
            )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text or "Failed to create branch")

        # Create PR
        r = await client.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={
                "title": pr_title,
                "body": pr_body,
                "head": branch_name,
                "base": base_branch,
            },
        )
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text or "Failed to create pull request")
        pr = r.json()

    return CreateSchemaPRResponse(
        pr_url=pr["html_url"],
        pr_number=pr["number"],
        branch=branch_name,
        commit_sha=commit_sha,
        file_path=file_path,
    )


# Include the API router
app.include_router(api_router)
