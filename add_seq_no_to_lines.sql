-- Migration script to add seq_no column to lines table
-- This script adds a nullable integer column for ordering lines within categories

-- Add the seq_no column to the lines table
ALTER TABLE lines 
ADD COLUMN seq_no INTEGER NULL;

-- Add a comment to document the column purpose
COMMENT ON COLUMN lines.seq_no IS 'Display sequence number for ordering lines within a category (nulls last)';

-- Optional: Create an index for better performance when ordering by seq_no
-- This index will help with ORDER BY seq_no, id queries
CREATE INDEX IF NOT EXISTS idx_lines_seq_no_id ON lines (seq_no, id);

-- Optional: Create a composite index for category-specific ordering
-- This index will help with queries that filter by categoryid and order by seq_no
CREATE INDEX IF NOT EXISTS idx_lines_category_seq_no_id ON lines (categoryid, seq_no, id);
