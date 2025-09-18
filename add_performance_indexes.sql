-- Performance optimization indexes for search_columns endpoint
-- Run this script on your database to improve query performance

-- Index for case-insensitive column name searches
CREATE INDEX IF NOT EXISTS idx_erp_column_name_lower 
ON erp_column (LOWER(name));

-- Index for column_id lookups in lines table (for category mappings)
CREATE INDEX IF NOT EXISTS idx_lines_column_id 
ON lines (column_id);

-- Index for categoryid lookups in lines table
CREATE INDEX IF NOT EXISTS idx_lines_categoryid 
ON lines (categoryid);

-- Composite index for the category mapping query
CREATE INDEX IF NOT EXISTS idx_lines_column_category 
ON lines (column_id, categoryid);

-- Index for table_id lookups in erp_column table
CREATE INDEX IF NOT EXISTS idx_erp_column_table_id 
ON erp_column (table_id);

-- Index for category name lookups (using correct column name "Name" with capital N)
CREATE INDEX IF NOT EXISTS idx_category_name 
ON category (Name);

-- Optional: Partial index for non-null column_id values in lines table
-- This can help with queries that filter out unmapped lines
CREATE INDEX IF NOT EXISTS idx_lines_column_id_not_null 
ON lines (column_id) 
WHERE column_id IS NOT NULL;

-- Optional: Index for category ID lookups
CREATE INDEX IF NOT EXISTS idx_category_id 
ON category (id);

-- Optional: Index for table ID lookups
CREATE INDEX IF NOT EXISTS idx_erp_table_id 
ON erp_table (id);

-- Additional indexes for better performance
-- Index for erp_column table_id foreign key
CREATE INDEX IF NOT EXISTS idx_erp_column_table_id_fk 
ON erp_column (table_id);

-- Index for lines table_id foreign key
CREATE INDEX IF NOT EXISTS idx_lines_table_id 
ON lines (table_id);

-- Index for lines sub_category_id foreign key
CREATE INDEX IF NOT EXISTS idx_lines_sub_category_id 
ON lines (sub_category_id);
