-- Migration script to add seq_no column to table_set table
-- This enables explicit ordering of table sets for upload-config generation and UI.

-- 1) Add the seq_no column (nullable for backward compatibility)
ALTER TABLE table_set
ADD COLUMN IF NOT EXISTS seq_no INTEGER NULL;

-- 2) Backfill existing rows so current order (by id) is preserved
UPDATE table_set
SET seq_no = id
WHERE seq_no IS NULL;

-- 3) Document purpose
COMMENT ON COLUMN table_set.seq_no IS 'Display sequence number for ordering table sets (nulls last). Backfilled to id for existing rows.';

-- 4) Index to support ORDER BY seq_no, id
CREATE INDEX IF NOT EXISTS idx_table_set_seq_no_id ON table_set (seq_no, id);

