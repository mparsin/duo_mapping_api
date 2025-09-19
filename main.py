from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db, Category, Lines, ERPTable, ERPColumn, SubCategory
from schemas import (
    Category as CategorySchema,
    Lines as LinesSchema,
    ERPTable as ERPTableSchema,
    ERPColumn as ERPColumnSchema,
    LineCreate,
    LineResponse,
    SubCategory as SubCategorySchema,
    SubCategoryUpdate,
    ColumnSearchResult,
    CategoryMappingInfo,
    TableMatchRequest,
    TableMatchResult
)
from typing import List, Dict, Any
from sqlalchemy import func
import json
from datetime import datetime

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

# Configure CORS - Update this section
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for public API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

# Helper function to calculate and update percent_mapped for a category
def update_category_percent_mapped(db: Session, category_id: int):
    """Calculate and update the percent_mapped field for a category"""
    # Get total lines count for this category (only lines with non-empty field_name and exclude=False)
    total_lines = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        Lines.field_name.isnot(None),
        Lines.field_name != "",
        Lines.exclude == False
    ).scalar()
    
    # Get total lines count for this category (all lines with non-empty field_name, regardless of exclude status)
    total_lines_all = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        Lines.field_name.isnot(None),
        Lines.field_name != ""
    ).scalar()
    
    if total_lines_all == 0:
        # No lines with field_name in category at all, set percent to 0
        percent_mapped = 0.0
    elif total_lines == 0:
        # All lines in category are excluded, set percent to 100 (task completed)
        percent_mapped = 100.0
    else:
        # Count mapped lines (lines that have both table_id and column_id AND non-empty field_name and exclude=False)
        mapped_lines = db.query(func.count(Lines.id)).filter(
            Lines.categoryid == category_id,
            Lines.field_name.isnot(None),
            Lines.field_name != "",
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
                "sub_category": line.sub_category.name if line.sub_category else None
            }
            
            # Add description field if reason is not null
            if line.reason is not None and line.reason.strip():
                column_entry["description"] = line.reason
            
            tables_dict[table_name]["columns"][column_name] = column_entry
    
    # Convert to final format (list of tables with columns as list)
    tables_list = []
    for table_data in tables_dict.values():
        table_entry = {
            "name": table_data["name"],
            "description": table_data["description"],
            "columns": list(table_data["columns"].values())
        }
        tables_list.append(table_entry)
    
    # Sort tables by name for consistent output
    tables_list.sort(key=lambda x: x["name"])
    
    return {
        "tables": tables_list,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_tables": len(tables_list),
        "total_mapped_columns": sum(len(table["columns"]) for table in tables_list)
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
    }
)
async def root():
    """
    **Welcome endpoint for the Duo Mapping API**
    
    This endpoint provides a simple health check and confirms the API is operational.
    Use this to verify the service is running before making other API calls.
    """
    return {"message": "Duo Mapping API is running"}

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
                            "epic": "Data Migration"
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
                        "epic": "Data Migration"
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
                            "column_name": "full_name"
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
    
    # Query lines with joined table and column information ordered by ID
    lines = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.categoryid == category_id).order_by(Lines.id).all()
    
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
            "exclude": line.exclude
        }
        result.append(line_dict)
    
    return result

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

@api_router.patch(
    "/lines/{line_id}",
    response_model=LineResponse,
    tags=["Lines"],
    summary="Update Line Mapping",
    description="Update an existing line mapping with new table/column assignments and comments",
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
            "description": "Invalid mapping (column doesn't belong to table)",
            "content": {
                "application/json": {
                    "example": {"detail": "Column does not belong to the specified table"}
                }
            }
        }
    }
)
async def update_line(line_id: int, line_data: LineCreate, db: Session = Depends(get_db)):
    """
    **Update line mapping**
    
    Updates an existing line with new table/column mappings and comments.
    
    - **line_id**: Unique identifier for the line to update
    - **line_data**: Update data (table_id, column_id, comment)
    
    Special behaviors:
    - Setting table_id to null/0 clears both table and column mappings
    - Setting column_id to 0 clears only the column mapping
    - Validates that columns belong to the specified table
    """
    # Find the line by ID
    existing_line = db.query(Lines).filter(Lines.id == line_id).first()
    if not existing_line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    # Handle comment update (can be done independently of table/column updates)
    if line_data.comment is not None:
        existing_line.comment = line_data.comment
    
    # Handle exclude update (can be done independently of table/column updates)
    if line_data.exclude is not None:
        existing_line.exclude = line_data.exclude
    
    # Handle table_id clearing logic
    if line_data.table_id is None or line_data.table_id == 0:
        # Clear table_id and column_id for the specific line only
        existing_line.table_id = None
        existing_line.column_id = None
        db.commit()
        
        # Update percent_mapped for the category
        update_category_percent_mapped(db, existing_line.categoryid)
        
        # Load the updated line for response
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
            "action": "cleared_table_id"
        }
    
    # Validate that the table exists
    table = db.query(ERPTable).filter(ERPTable.id == line_data.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="ERP table not found")
    
    # Update the line's table_id
    existing_line.table_id = line_data.table_id
    
    # Handle column_id clearing logic
    if line_data.column_id == 0:
        # Clear column_id for the specific line only
        existing_line.column_id = None
    elif line_data.column_id is not None:
        # Validate that the column exists
        column = db.query(ERPColumn).filter(ERPColumn.id == line_data.column_id).first()
        if not column:
            raise HTTPException(status_code=404, detail="ERP column not found")
        
        # Validate that the column belongs to the specified table
        if column.table_id != line_data.table_id:
            raise HTTPException(status_code=400, detail="Column does not belong to the specified table")
        
        # Update the column_id and name
        existing_line.column_id = line_data.column_id
    else:
        # If column_id is not provided, set it to None and update name to just table name
        existing_line.column_id = None
    
    db.commit()
    db.refresh(existing_line)
    
    # Update percent_mapped for the category
    update_category_percent_mapped(db, existing_line.categoryid)
    
    # Load the related table and column data for the response
    updated_line = db.query(Lines).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
    ).filter(Lines.id == existing_line.id).first()
    
    action = "cleared_column_id" if line_data.column_id == 0 else "updated"
    
    return {
        "id": updated_line.id,
        "categoryid": updated_line.categoryid,
        "table_id": updated_line.table_id,
        "column_id": updated_line.column_id,
        "table_name": updated_line.erp_table.name if updated_line.erp_table else None,
        "column_name": updated_line.erp_column.name if updated_line.erp_column else None,
        "comment": updated_line.comment,
        "exclude": updated_line.exclude,
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
    "/health",
    tags=["Utilities"],
    summary="Health Check",
    description="Simple health check to verify API availability",
    responses={
        200: {
            "description": "API is healthy and operational",
            "content": {
                "application/json": {
                    "example": {"status": "healthy"}
                }
            }
        }
    }
)
async def health_check():
    """
    **API health check**
    
    Simple endpoint to verify the API is running and operational.
    Use this for monitoring and load balancer health checks.
    """
    return {"status": "healthy"}

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
                                        "description": "Primary customer identifier"
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

# Include the API router
app.include_router(api_router)
