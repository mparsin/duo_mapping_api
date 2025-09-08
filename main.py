from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, joinedload
from database import get_db, Category, Lines, ERPTable, ERPColumn, SubCategory
from schemas import Category as CategorySchema, Lines as LinesSchema, ERPTable as ERPTableSchema, ERPColumn as ERPColumnSchema, LineCreate, LineResponse, SubCategory as SubCategorySchema, ColumnSearchResult
from typing import List

app = FastAPI(title="Duo Mapping API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API router with /api prefix
from fastapi import APIRouter
api_router = APIRouter(prefix="/api")

@app.get("/")
async def root():
    return {"message": "Duo Mapping API is running"}

# API endpoints with /api prefix
@api_router.get("/categories", response_model=List[CategorySchema])
async def get_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).all()
    return categories

@api_router.get("/categories/{category_id}/sub-categories", response_model=List[SubCategorySchema])
async def get_sub_categories_by_category(category_id: int, db: Session = Depends(get_db)):
    """Get all sub-categories for a specific category ordered by sub-category ID"""
    # Check if category exists
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Query sub-categories for the category ordered by ID
    sub_categories = db.query(SubCategory).filter(SubCategory.category_id == category_id).order_by(SubCategory.id).all()
    return sub_categories

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
    """Update existing line by ID with new table_id and optionally column_id"""
    # Find the line by ID
    existing_line = db.query(Lines).filter(Lines.id == line_id).first()
    if not existing_line:
        raise HTTPException(status_code=404, detail="Line not found")
    
    # Handle table_id clearing logic
    if line_data.table_id is None or line_data.table_id == 0:
        # Clear table_id and column_id for the specific line only
        existing_line.table_id = None
        existing_line.column_id = None
        db.commit()
        
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

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Include the API router
app.include_router(api_router)
