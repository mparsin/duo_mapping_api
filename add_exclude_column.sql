-- Migration script to add exclude column to lines table
-- This script adds a new boolean column 'exclude' to the lines table
-- with a default value of FALSE for backward compatibility

-- Add the exclude column to the lines table
ALTER TABLE lines 
ADD COLUMN exclude BOOLEAN NOT NULL DEFAULT FALSE;

-- Add a comment to document the column's purpose
COMMENT ON COLUMN lines.exclude IS 'When true, this line should be excluded from all percentage calculations related to mapping';

-- Create an index on the exclude column for better query performance
-- This will help with the percentage calculation queries that filter by exclude = FALSE
CREATE INDEX idx_lines_exclude ON lines(exclude);

-- Optional: Create a composite index for the percentage calculation queries
-- This index will be very efficient for the specific query pattern used in update_category_percent_mapped
CREATE INDEX idx_lines_category_exclude_field_name ON lines(categoryid, exclude, field_name) 
WHERE field_name IS NOT NULL AND field_name != '';

-- Optional: Create another composite index for mapped lines queries
CREATE INDEX idx_lines_category_exclude_mapped ON lines(categoryid, exclude, table_id, column_id)
WHERE table_id IS NOT NULL AND column_id IS NOT NULL;

-- Verify the column was added successfully
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'lines' AND column_name = 'exclude';
