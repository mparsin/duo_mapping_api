from pydantic import BaseModel
from typing import Optional, List

# Category schemas
class CategoryBase(BaseModel):
    Name: str

class Category(CategoryBase):
    id: int
    percent_mapped: float = 0.0
    
    class Config:
        from_attributes = True

# Lines schemas
class LinesBase(BaseModel):
    default: Optional[str] = None
    customer_settings: Optional[str] = None
    no_of_chars: Optional[str] = None
    field_name: Optional[str] = None
    reason: Optional[str] = None
    name: str
    comment: Optional[str] = None
    sub_category_id: Optional[int] = None
    table_id: Optional[int] = None
    column_id: Optional[int] = None

class Lines(LinesBase):
    id: int
    categoryid: int
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    
    class Config:
        from_attributes = True

# SubCategory schemas
class SubCategoryBase(BaseModel):
    name: str
    category_id: int

class SubCategory(SubCategoryBase):
    id: int
    
    class Config:
        from_attributes = True

# ERP Table schemas
class ERPTableBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ERPTable(ERPTableBase):
    id: int
    
    class Config:
        from_attributes = True

# ERP Column schemas
class ERPColumnBase(BaseModel):
    name: str
    comment: Optional[str] = None
    type: Optional[str] = None
    table_id: Optional[int] = None

class ERPColumn(ERPColumnBase):
    id: int
    
    class Config:
        from_attributes = True

# Line creation schemas
class LineCreate(BaseModel):
    table_id: Optional[int] = None
    column_id: Optional[int] = None
    comment: Optional[str] = None

class LineResponse(BaseModel):
    id: int
    categoryid: int
    table_id: Optional[int] = None
    column_id: Optional[int] = None
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    comment: Optional[str] = None
    action: str  # "updated"
    
    class Config:
        from_attributes = True

# Column search response schema
class ColumnSearchResult(BaseModel):
    column_name: str
    table_name: str
    column_id: int
    table_id: int
    match_type: str  # "exact" or "partial"
    
    class Config:
        from_attributes = True

# Table match request schema
class TableMatchRequest(BaseModel):
    column_names: List[str]

# Table match result schema
class TableMatchResult(BaseModel):
    table_id: int
    table_name: str
    match_count: int
    matched_columns: List[str]
    
    class Config:
        from_attributes = True




