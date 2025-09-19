-- Additional indexes specifically optimized for find-table-matches endpoint
-- These indexes will significantly improve the performance of table matching queries

-- Index for the main table matching query (ERPColumn.name with table_id)
-- This covers the JOIN between erp_column and erp_table
CREATE INDEX IF NOT EXISTS idx_erp_column_name_table_id 
ON erp_column (name, table_id);

-- Index for case-insensitive column name lookups with table_id
-- This is specifically for the IN clause with LOWER() function
CREATE INDEX IF NOT EXISTS idx_erp_column_lower_name_table_id 
ON erp_column (LOWER(name), table_id);

-- Index for erp_table.id lookups (should already exist but ensuring it's there)
CREATE INDEX IF NOT EXISTS idx_erp_table_id_lookup 
ON erp_table (id);

-- Index for erp_table.name lookups (for sorting by table name)
CREATE INDEX IF NOT EXISTS idx_erp_table_name 
ON erp_table (name);

-- Composite index for the exact query pattern used in find-table-matches
-- This covers: SELECT name, table_id FROM erp_column WHERE LOWER(name) IN (...)
CREATE INDEX IF NOT EXISTS idx_erp_column_lower_name_covering 
ON erp_column (LOWER(name)) INCLUDE (name, table_id);

-- If the above INCLUDE syntax is not supported (older PostgreSQL versions),
-- use this alternative:
-- CREATE INDEX IF NOT EXISTS idx_erp_column_lower_name_covering_alt 
-- ON erp_column (LOWER(name), name, table_id);

-- Index for table_id foreign key in erp_column (should already exist)
CREATE INDEX IF NOT EXISTS idx_erp_column_table_id_fk 
ON erp_column (table_id);

-- Statistics update to help query planner make better decisions
-- Run this after creating the indexes
-- ANALYZE erp_column;
-- ANALYZE erp_table;
