from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

# TableSet schemas
class TableSetBase(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Table set name",
        example="Master Data"
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering table sets (nulls last)",
        example=1
    )

class TableSetCreate(BaseModel):
    name: str = Field(
        ...,
        description="Table set name",
        example="Master Data"
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering table sets (nulls last)",
        example=1
    )

class TableSetUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="Updated table set name",
        example="Master Data"
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Updated display sequence number for ordering table sets (nulls last)",
        example=1
    )

class TableSetReorderItem(BaseModel):
    id: int = Field(
        ...,
        description="Unique table set identifier",
        example=1
    )
    seq_no: int = Field(
        ...,
        description="New sequence number for ordering table sets",
        example=10
    )

class TableSetReorderRequest(BaseModel):
    items: List[TableSetReorderItem] = Field(
        ...,
        description="List of table sets with their desired sequence numbers",
        min_items=1,
        example=[{"id": 1, "seq_no": 10}, {"id": 2, "seq_no": 20}]
    )

class TableSet(TableSetBase):
    id: int = Field(
        ...,
        description="Unique table set identifier",
        example=1
    )
    
    class Config:
        from_attributes = True

# Category schemas
class CategoryBase(BaseModel):
    Name: str = Field(
        ...,
        description="Category name",
        example="Customer Data"
    )

class Category(CategoryBase):
    id: int = Field(
        ...,
        description="Unique category identifier",
        example=1
    )
    percent_mapped: float = Field(
        default=0.0,
        description="Percentage of lines mapped in this category (0-100)",
        example=75.5,
        ge=0,
        le=100
    )
    tab: Optional[str] = Field(
        default=None,
        description="UI tab association for grouping categories",
        example="customers"
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering categories",
        example=1
    )
    line_no: Optional[int] = Field(
        default=None,
        description="Line number for ordering categories within table sets",
        example=1
    )
    epic: Optional[str] = Field(
        default=None,
        description="Associated epic or project identifier",
        example="Data Migration"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration settings for this category as JSON",
        example={"theme": "blue", "enabled": True}
    )
    isaiload: bool = Field(
        default=False,
        description="Whether this category is an AI load category",
        example=False
    )
    table_set_id: Optional[int] = Field(
        default=None,
        description="Associated table set identifier for grouping categories",
        example=1
    )
    
    class Config:
        from_attributes = True

# Category upload-config editor schemas
class CategoryUploadMetadataUpdate(BaseModel):
    Name: Optional[str] = Field(
        default=None,
        description="Optional updated category name (used as table label in UI)",
        example="Customer Master Data"
    )
    table_set_id: Optional[int] = Field(
        default=None,
        description="Assign category to a table set (null to unassign)",
        example=1
    )
    line_no: Optional[int] = Field(
        default=None,
        description="Ordering number for tables within a table set (nulls last)",
        example=10
    )

class CategoryUploadOrderItem(BaseModel):
    category_id: int = Field(
        ...,
        description="Category identifier to update",
        example=123
    )
    table_set_id: Optional[int] = Field(
        default=None,
        description="Assign category to a table set (null to unassign)",
        example=1
    )
    line_no: Optional[int] = Field(
        default=None,
        description="Ordering number for tables within a table set (nulls last)",
        example=10
    )

class CategoryUploadOrderRequest(BaseModel):
    items: List[CategoryUploadOrderItem] = Field(
        ...,
        description="Bulk updates to category table-set assignment and ordering",
        min_items=1,
        example={
            "items": [
                {"category_id": 101, "table_set_id": 1, "line_no": 10},
                {"category_id": 102, "table_set_id": 1, "line_no": 20},
                {"category_id": 103, "table_set_id": None, "line_no": None}
            ]
        }
    )

class UploadConfigEditorTable(BaseModel):
    category_id: int = Field(..., description="Category identifier", example=101)
    category_name: str = Field(..., description="Category name", example="Users")
    table_set_id: Optional[int] = Field(default=None, description="Assigned table set id", example=1)
    line_no: Optional[int] = Field(default=None, description="Order within set (nulls last)", example=10)
    config: Optional[Dict[str, Any]] = Field(default=None, description="Category config JSON", example={"table": "users", "batch_size": 1, "endpoint": "api/users/load"})
    table: Optional[str] = Field(default=None, description="Convenience field derived from config.table", example="users")
    batch_size: Optional[int] = Field(default=None, description="Convenience field derived from config.batch_size", example=1)
    endpoint: Optional[str] = Field(default=None, description="Convenience field derived from config.endpoint", example="api/users/load")
    related_tables: Optional[Any] = Field(default=None, description="Convenience field derived from config.related_tables")

class UploadConfigEditorSet(BaseModel):
    table_set_id: int = Field(..., description="Table set identifier", example=1)
    set_name: Optional[str] = Field(default=None, description="Table set name", example="Master Data")
    seq_no: Optional[int] = Field(default=None, description="Table set ordering number (nulls last)", example=10)
    tables: List[UploadConfigEditorTable] = Field(default=[], description="Tables (categories) assigned to this set")

class UploadConfigEditorResponse(BaseModel):
    sets: List[UploadConfigEditorSet] = Field(default=[], description="All table sets with their assigned tables")
    unassigned: List[UploadConfigEditorTable] = Field(default=[], description="Tables (categories) with config but no table_set_id")
    generated_at: str = Field(..., description="Response generation timestamp (UTC ISO8601)", example="2026-01-29T12:00:00Z")

# Category config schemas
class CategoryConfigUpdate(BaseModel):
    config: Dict[str, Any] = Field(
        ...,
        description="Configuration settings for this category as JSON",
        example={"theme": "blue", "enabled": True, "settings": {"auto_save": True}}
    )

class CategoryConfigResponse(BaseModel):
    id: int = Field(
        ...,
        description="Unique category identifier",
        example=1
    )
    Name: str = Field(
        ...,
        description="Category name",
        example="Customer Data"
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Configuration settings for this category as JSON",
        example={"theme": "blue", "enabled": True}
    )
    isaiload: bool = Field(
        default=False,
        description="Whether this category is an AI load category",
        example=False
    )
    message: str = Field(
        ...,
        description="Operation result message",
        example="Config successfully updated"
    )
    
    class Config:
        from_attributes = True

# Lines schemas
class LinesBase(BaseModel):
    default: Optional[str] = Field(
        default=None,
        description="Default value for this field",
        example="John Doe"
    )
    customer_settings: Optional[str] = Field(
        default=None,
        description="Customer-specific configuration settings",
        example="required"
    )
    no_of_chars: Optional[str] = Field(
        default=None,
        description="Maximum character length for this field",
        example="50"
    )
    field_name: Optional[str] = Field(
        default=None,
        description="Source field name in the original system",
        example="customer_name"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Explanation or justification for this mapping",
        example="Primary customer identifier used across all systems"
    )
    name: str = Field(
        ...,
        description="Display name for this line/field",
        example="Customer Name"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Additional notes or comments about this mapping",
        example="Full customer name including middle initial"
    )
    sub_category_id: Optional[int] = Field(
        default=None,
        description="Associated sub-category identifier",
        example=1
    )
    table_id: Optional[int] = Field(
        default=None,
        description="Target ERP table identifier",
        example=5
    )
    column_id: Optional[int] = Field(
        default=None,
        description="Target ERP column identifier",
        example=23
    )
    exclude: Optional[bool] = Field(
        default=False,
        description="Whether this line should be excluded from percentage calculations",
        example=False
    )
    iskeyfield: Optional[bool] = Field(
        default=False,
        description="Whether this line represents a key field",
        example=False
    )
    isfkfield: Optional[bool] = Field(
        default=False,
        description="Whether this line represents a foreign key field",
        example=False
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering lines",
        example=1
    )

class Lines(LinesBase):
    id: int = Field(
        ...,
        description="Unique line identifier",
        example=1
    )
    categoryid: int = Field(
        ...,
        description="Parent category identifier",
        example=1
    )
    table_name: Optional[str] = Field(
        default=None,
        description="Target ERP table name (populated from table_id)",
        example="customers"
    )
    column_name: Optional[str] = Field(
        default=None,
        description="Target ERP column name (populated from column_id)",
        example="full_name"
    )
    exclude: bool = Field(
        default=False,
        description="Whether this line should be excluded from percentage calculations",
        example=False
    )
    iskeyfield: bool = Field(
        default=False,
        description="Whether this line represents a key field",
        example=False
    )
    isfkfield: bool = Field(
        default=False,
        description="Whether this line represents a foreign key field",
        example=False
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering lines",
        example=1
    )
    
    class Config:
        from_attributes = True

# SubCategory schemas
class SubCategoryBase(BaseModel):
    name: str = Field(
        ...,
        description="Sub-category name",
        example="Personal Information"
    )
    category_id: int = Field(
        ...,
        description="Parent category identifier",
        example=1
    )
    comment: Optional[str] = Field(
        default=None,
        description="Additional notes about this sub-category",
        example="Customer personal details and identification"
    )
    seq_no: Optional[int] = Field(
        default=None,
        description="Display sequence number for ordering sub-categories",
        example=1
    )

class SubCategory(SubCategoryBase):
    id: int = Field(
        ...,
        description="Unique sub-category identifier",
        example=1
    )
    
    class Config:
        from_attributes = True

# SubCategory update schema (only comment is editable)
class SubCategoryUpdate(BaseModel):
    comment: Optional[str] = Field(
        default=None,
        description="Updated comment for the sub-category",
        example="Updated customer personal details and identification"
    )

# ERP Table schemas
class ERPTableBase(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description="ERP table name",
        example="customers"
    )
    description: Optional[str] = Field(
        default=None,
        description="Table description or purpose",
        example="Customer master data table"
    )

class ERPTable(ERPTableBase):
    id: int = Field(
        ...,
        description="Unique table identifier",
        example=1
    )
    
    class Config:
        from_attributes = True

# ERP Column schemas
class ERPColumnBase(BaseModel):
    name: str = Field(
        ...,
        description="Column name in the ERP table",
        example="customer_id"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Column comment or description",
        example="Unique customer identifier"
    )
    type: Optional[str] = Field(
        default=None,
        description="Column data type",
        example="integer"
    )
    table_id: Optional[int] = Field(
        default=None,
        description="Parent table identifier",
        example=1
    )
    not_null: Optional[bool] = Field(
        default=False,
        description="Whether the column requires a value (NOT NULL constraint)",
        example=True
    )
    primary_key: Optional[bool] = Field(
        default=False,
        description="Whether this column is part of the primary key",
        example=True
    )
    unique: Optional[bool] = Field(
        default=False,
        description="Whether this column has a unique constraint",
        example=True
    )
    default: Optional[str] = Field(
        default=None,
        description="Default value for the column",
        example="0"
    )

class ERPColumn(ERPColumnBase):
    id: int = Field(
        ...,
        description="Unique column identifier",
        example=1
    )
    
    class Config:
        from_attributes = True

# Line creation schemas
class LineCreate(BaseModel):
    table_id: Optional[int] = Field(
        default=None,
        description="Target ERP table ID (set to 0 or null to clear mapping)",
        example=5
    )
    column_id: Optional[int] = Field(
        default=None,
        description="Target ERP column ID (set to 0 to clear column only)",
        example=23
    )
    comment: Optional[str] = Field(
        default=None,
        description="Comment about this mapping",
        example="Mapped to primary customer name field"
    )
    exclude: Optional[bool] = Field(
        default=False,
        description="Whether this line should be excluded from percentage calculations",
        example=False
    )
    iskeyfield: Optional[bool] = Field(
        default=None,
        description="Whether this line represents a key field",
        example=False
    )
    isfkfield: Optional[bool] = Field(
        default=None,
        description="Whether this line represents a foreign key field",
        example=False
    )

class LineResponse(BaseModel):
    id: int = Field(
        ...,
        description="Line identifier",
        example=1
    )
    categoryid: int = Field(
        ...,
        description="Category identifier",
        example=1
    )
    table_id: Optional[int] = Field(
        default=None,
        description="Mapped table identifier",
        example=5
    )
    column_id: Optional[int] = Field(
        default=None,
        description="Mapped column identifier",
        example=23
    )
    table_name: Optional[str] = Field(
        default=None,
        description="Mapped table name",
        example="customers"
    )
    column_name: Optional[str] = Field(
        default=None,
        description="Mapped column name",
        example="full_name"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Mapping comment",
        example="Mapped to primary customer name field"
    )
    exclude: bool = Field(
        default=False,
        description="Whether this line should be excluded from percentage calculations",
        example=False
    )
    iskeyfield: bool = Field(
        default=False,
        description="Whether this line represents a key field",
        example=False
    )
    isfkfield: bool = Field(
        default=False,
        description="Whether this line represents a foreign key field",
        example=False
    )
    action: str = Field(
        ...,
        description="Action performed (updated, cleared_table_id, cleared_column_id)",
        example="updated"
    )
    
    class Config:
        from_attributes = True

# Category mapping info schema
class CategoryMappingInfo(BaseModel):
    id: int = Field(
        ...,
        description="Unique category identifier",
        example=1
    )
    name: str = Field(
        ...,
        description="Category name",
        example="Customer Data"
    )
    
    class Config:
        from_attributes = True

# Column search response schema
class ColumnSearchResult(BaseModel):
    column_name: str = Field(
        ...,
        description="Name of the matching column",
        example="customer_name"
    )
    table_name: str = Field(
        ...,
        description="Name of the table containing this column",
        example="customers"
    )
    column_id: int = Field(
        ...,
        description="Unique identifier for the column",
        example=23
    )
    table_id: int = Field(
        ...,
        description="Unique identifier for the table",
        example=5
    )
    match_type: str = Field(
        ...,
        description="Type of match found (exact or partial)",
        example="exact",
        pattern="^(exact|partial)$"
    )
    mapped_categories: List[CategoryMappingInfo] = Field(
        default=[],
        description="List of categories where this column is mapped, including ID and name",
        example=[
            {"id": 1, "name": "Customer Data"},
            {"id": 2, "name": "Order Management"}
        ]
    )
    
    class Config:
        from_attributes = True

# Table match request schema
class TableMatchRequest(BaseModel):
    column_names: List[str] = Field(
        ...,
        description="List of column names to find matches for",
        example=["customer_name", "email", "phone", "address"],
        min_items=1
    )

# Table match result schema
class TableMatchResult(BaseModel):
    table_id: int = Field(
        ...,
        description="Unique identifier for the matching table",
        example=5
    )
    table_name: str = Field(
        ...,
        description="Name of the matching table",
        example="customers"
    )
    match_count: int = Field(
        ...,
        description="Number of columns that matched in this table",
        example=3
    )
    matched_columns: List[str] = Field(
        ...,
        description="List of column names that matched",
        example=["customer_name", "email", "phone"]
    )
    
    class Config:
        from_attributes = True




