#!/usr/bin/env python3
"""
Create indexes specifically optimized for find-table-matches endpoint
"""
from database import engine
from sqlalchemy import text
import time

def create_table_matching_indexes():
    """Create indexes optimized for table matching queries"""
    
    indexes = [
        "-- Index for the main table matching query (ERPColumn.name with table_id)",
        "CREATE INDEX IF NOT EXISTS idx_erp_column_name_table_id ON erp_column (name, table_id);",
        
        "-- Index for case-insensitive column name lookups with table_id",
        "CREATE INDEX IF NOT EXISTS idx_erp_column_lower_name_table_id ON erp_column (LOWER(name), table_id);",
        
        "-- Index for erp_table.id lookups",
        "CREATE INDEX IF NOT EXISTS idx_erp_table_id_lookup ON erp_table (id);",
        
        "-- Index for erp_table.name lookups (for sorting by table name)",
        "CREATE INDEX IF NOT EXISTS idx_erp_table_name ON erp_table (name);",
        
        "-- Index for table_id foreign key in erp_column",
        "CREATE INDEX IF NOT EXISTS idx_erp_column_table_id_fk ON erp_column (table_id);",
        
        "-- Update statistics to help query planner",
        "ANALYZE erp_column;",
        "ANALYZE erp_table;"
    ]
    
    print("Creating table matching performance indexes...")
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
    print("Table matching indexes creation completed!")
    print("\nYou can now test the performance improvements with:")
    print("  python test_table_matching_performance.py")

if __name__ == "__main__":
    create_table_matching_indexes()
