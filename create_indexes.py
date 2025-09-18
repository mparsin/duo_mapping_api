#!/usr/bin/env python3
"""
Safely create performance indexes for the Duo Mapping API
"""
from database import engine
from sqlalchemy import text
import time

def create_indexes():
    """Create all performance indexes safely"""
    
    indexes = [
        "-- Index for case-insensitive column name searches",
        "CREATE INDEX IF NOT EXISTS idx_erp_column_name_lower ON erp_column (LOWER(name));",
        
        "-- Index for column_id lookups in lines table",
        "CREATE INDEX IF NOT EXISTS idx_lines_column_id ON lines (column_id);",
        
        "-- Index for categoryid lookups in lines table", 
        "CREATE INDEX IF NOT EXISTS idx_lines_categoryid ON lines (categoryid);",
        
        "-- Composite index for the category mapping query",
        "CREATE INDEX IF NOT EXISTS idx_lines_column_category ON lines (column_id, categoryid);",
        
        "-- Index for table_id lookups in erp_column table",
        "CREATE INDEX IF NOT EXISTS idx_erp_column_table_id ON erp_column (table_id);",
        
        "-- Index for category name lookups (using correct column name)",
        "CREATE INDEX IF NOT EXISTS idx_category_name ON category (\"Name\");",
        
        "-- Partial index for non-null column_id values",
        "CREATE INDEX IF NOT EXISTS idx_lines_column_id_not_null ON lines (column_id) WHERE column_id IS NOT NULL;",
        
        "-- Index for category ID lookups",
        "CREATE INDEX IF NOT EXISTS idx_category_id ON category (id);",
        
        "-- Index for table ID lookups",
        "CREATE INDEX IF NOT EXISTS idx_erp_table_id ON erp_table (id);",
        
        "-- Additional foreign key indexes",
        "CREATE INDEX IF NOT EXISTS idx_lines_table_id ON lines (table_id);",
        "CREATE INDEX IF NOT EXISTS idx_lines_sub_category_id ON lines (sub_category_id);"
    ]
    
    print("Creating performance indexes...")
    print("=" * 50)
    
    with engine.connect() as conn:
        for i, sql in enumerate(indexes, 1):
            if sql.startswith("--"):
                print(f"\n{sql}")
                continue
                
            try:
                start_time = time.time()
                conn.execute(text(sql))
                conn.commit()
                end_time = time.time()
                
                print(f"✅ Index {i}: Created successfully ({end_time - start_time:.3f}s)")
                
            except Exception as e:
                print(f"❌ Index {i}: Failed - {e}")
                # Rollback the failed transaction and continue
                conn.rollback()
                continue
    
    print("\n" + "=" * 50)
    print("Index creation completed!")
    print("\nYou can now test the performance improvements with:")
    print("  python performance_test.py")

if __name__ == "__main__":
    create_indexes()
