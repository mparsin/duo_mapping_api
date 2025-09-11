from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from database import get_db, Category, Lines, ERPTable, ERPColumn, SubCategory
from schemas import Category as CategorySchema, Lines as LinesSchema, ERPTable as ERPTableSchema, ERPColumn as ERPColumnSchema, LineCreate, LineResponse, SubCategory as SubCategorySchema, SubCategoryUpdate, ColumnSearchResult, TableMatchRequest, TableMatchResult
from typing import List, Dict, Any
from sqlalchemy import func
import json
from datetime import datetime

app = FastAPI(title="Duo Mapping API", version="1.0.0")

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
    # Get total lines count for this category (only lines with non-empty field_name)
    total_lines = db.query(func.count(Lines.id)).filter(
        Lines.categoryid == category_id,
        Lines.field_name.isnot(None),
        Lines.field_name != ""
    ).scalar()
    
    if total_lines == 0:
        # No lines with field_name in category, set percent to 0
        percent_mapped = 0.0
    else:
        # Count mapped lines (lines that have both table_id and column_id AND non-empty field_name)
        mapped_lines = db.query(func.count(Lines.id)).filter(
            Lines.categoryid == category_id,
            Lines.field_name.isnot(None),
            Lines.field_name != "",
            Lines.table_id.isnot(None),
            Lines.column_id.isnot(None)
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
    
    # Get all mapped lines (lines that have both table_id and column_id)
    mapped_lines = db.query(Lines).filter(
        Lines.table_id.isnot(None),
        Lines.column_id.isnot(None)
    ).options(
        joinedload(Lines.erp_table),
        joinedload(Lines.erp_column)
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
                "comment": column.comment
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

@app.get("/")
async def root():
    return {"message": "Duo Mapping API is running"}

# API endpoints with /api prefix
@api_router.get("/categories", response_model=List[CategorySchema])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories ordered by seq_no"""
    categories = db.query(Category).order_by(Category.seq_no).all()
    return categories

@api_router.get("/categories/{category_id}", response_model=CategorySchema)
async def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a specific category by ID"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category

@api_router.get("/categories/{category_id}/sub-categories", response_model=List[SubCategorySchema])
async def get_sub_categories_by_category(category_id: int, db: Session = Depends(get_db)):
    """Get all sub-categories for a specific category ordered by seq_no (fallback to ID when seq_no is null)"""
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Query sub-categories for the category ordered by seq_no (nulls last), then by ID
    sub_categories = db.query(SubCategory).filter(SubCategory.category_id == category_id).order_by(SubCategory.seq_no.nulls_last(), SubCategory.id).all()
    return sub_categories

@api_router.get("/categories/{category_id}/sub-categories/{sub_category_id}", response_model=SubCategorySchema)
async def get_sub_category(category_id: int, sub_category_id: int, db: Session = Depends(get_db)):
    """Get a specific sub-category by ID within a category"""
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

@api_router.patch("/categories/{category_id}/sub-categories/{sub_category_id}", response_model=SubCategorySchema)
async def update_sub_category_comment(
    category_id: int, 
    sub_category_id: int, 
    sub_category_data: SubCategoryUpdate, 
    db: Session = Depends(get_db)
):
    """Update a sub-category's comment (name is not editable)"""
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

@api_router.get("/categories/{category_id}/lines", response_model=List[LinesSchema])
async def get_lines_by_category(category_id: int, db: Session = Depends(get_db)):
    """Get all lines for a specific category with table and column names"""
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
            "column_name": line.erp_column.name if line.erp_column else None
        }
        result.append(line_dict)
    
    return result

@api_router.get("/tables", response_model=List[ERPTableSchema])
async def get_erp_tables(db: Session = Depends(get_db)):
    """Get all ERP tables"""
    erp_tables = db.query(ERPTable).all()
    return erp_tables

@api_router.get("/tables/{table_id}/columns", response_model=List[ERPColumnSchema])
async def get_erp_columns_by_table(table_id: int, db: Session = Depends(get_db)):
    """Get all columns for a specific ERP table"""
    # Check if table exists
    erp_table = db.query(ERPTable).filter(ERPTable.id == table_id).first()
    if not erp_table:
        raise HTTPException(status_code=404, detail="ERP table not found")
    
    columns = db.query(ERPColumn).filter(ERPColumn.table_id == table_id).all()
    return columns

@api_router.patch("/lines/{line_id}", response_model=LineResponse)
async def update_line(line_id: int, line_data: LineCreate, db: Session = Depends(get_db)):
    """Update existing line by ID with new table_id, optionally column_id, and optionally comment"""
    # Find the line by ID
    existing_line = db.query(Lines).filter(Lines.id == line_id).first()
    if not existing_line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    # Handle comment update (can be done independently of table/column updates)
    if line_data.comment is not None:
        existing_line.comment = line_data.comment
    
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
        "action": action
    }

@api_router.get("/search-columns", response_model=List[ColumnSearchResult])
async def search_columns(columnName: str, db: Session = Depends(get_db)):
    """Search through all columns by name, returning exact matches first, then partial matches"""
    if not columnName or not columnName.strip():
        raise HTTPException(status_code=400, detail="columnName parameter is required and cannot be empty")
    
    # Clean the search term
    search_term = columnName.strip().lower()
    
    # Query all columns with their table information
    columns = db.query(ERPColumn, ERPTable).join(ERPTable, ERPColumn.table_id == ERPTable.id).all()
    
    exact_matches = []
    partial_matches = []
    
    for column, table in columns:
        column_name_lower = column.name.lower()
        
        # Check for exact match
        if column_name_lower == search_term:
            exact_matches.append(ColumnSearchResult(
                column_name=column.name,
                table_name=table.name,
                column_id=column.id,
                table_id=table.id,
                match_type="exact"
            ))
        # Check for partial match (contains the search term)
        elif search_term in column_name_lower:
            partial_matches.append(ColumnSearchResult(
                column_name=column.name,
                table_name=table.name,
                column_id=column.id,
                table_id=table.id,
                match_type="partial"
            ))
    
    # Return exact matches first, then partial matches
    return exact_matches + partial_matches

@api_router.post("/find-table-matches", response_model=List[TableMatchResult])
async def find_table_matches(request: TableMatchRequest, db: Session = Depends(get_db)):
    """Find tables with the most column matches from a list of column names"""
    if not request.column_names or len(request.column_names) == 0:
        raise HTTPException(status_code=400, detail="column_names list cannot be empty")
    
    # Clean and normalize column names for case-insensitive matching
    search_columns = [col.strip().lower() for col in request.column_names if col.strip()]
    
    if not search_columns:
        raise HTTPException(status_code=400, detail="No valid column names provided")
    
    # Get all tables with their columns
    tables = db.query(ERPTable).options(joinedload(ERPTable.columns)).all()
    
    table_matches = []
    
    for table in tables:
        matched_columns = []
        match_count = 0
        
        # Check each column in the table against our search list
        for column in table.columns:
            column_name_lower = column.name.lower()
            
            # Check for exact matches only
            if column_name_lower in search_columns:
                matched_columns.append(column.name)
                match_count += 1
        
        # Only include tables that have at least one match
        if match_count > 0:
            table_matches.append(TableMatchResult(
                table_id=table.id,
                table_name=table.name,
                match_count=match_count,
                matched_columns=matched_columns
            ))
    
    # Sort by match count (descending) and then by table name (ascending) for consistent ordering
    table_matches.sort(key=lambda x: (-x.match_count, x.table_name))
    
    return table_matches

@api_router.post("/categories/recalculate-percent-mapped")
async def recalculate_all_percent_mapped(db: Session = Depends(get_db)):
    """Recalculate percent_mapped for all categories"""
    categories = db.query(Category).all()
    updated_count = 0
    
    for category in categories:
        update_category_percent_mapped(db, category.id)
        updated_count += 1
    
    return {
        "message": f"Successfully recalculated percent_mapped for {updated_count} categories",
        "updated_count": updated_count
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@api_router.get("/download-schema")
async def download_schema(db: Session = Depends(get_db)):
    """Generate and download schema file containing only mapped tables and columns"""
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
