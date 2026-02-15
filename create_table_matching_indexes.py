#!/usr/bin/env python3
"""
Create indexes specifically optimized for find-table-matches endpoint.
All tables live in the "app" schema. DDL requires app_migrator.
Uses DATABASE_MIGRATOR_URL if set, otherwise DATABASE_URL (must be app_migrator for this script).
"""
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
import time

# DDL scripts must run as app_migrator. Prefer DATABASE_MIGRATOR_URL when set.
_db_url = os.getenv("DATABASE_MIGRATOR_URL") or os.getenv("DATABASE_URL")
engine = create_engine(_db_url)

# Schema where all app tables live (DDL must run as app_migrator).
SCHEMA = "app"

def create_table_matching_indexes():
    """Create indexes optimized for table matching queries"""
    
    indexes = [
        "-- Index for the main table matching query (ERPColumn.name with table_id)",
        f"CREATE INDEX IF NOT EXISTS idx_erp_column_name_table_id ON {SCHEMA}.erp_column (name, table_id);",
        
        "-- Index for case-insensitive column name lookups with table_id",
        f"CREATE INDEX IF NOT EXISTS idx_erp_column_lower_name_table_id ON {SCHEMA}.erp_column (LOWER(name), table_id);",
        
        "-- Index for erp_table.id lookups",
        f"CREATE INDEX IF NOT EXISTS idx_erp_table_id_lookup ON {SCHEMA}.erp_table (id);",
        
        "-- Index for erp_table.name lookups (for sorting by table name)",
        f"CREATE INDEX IF NOT EXISTS idx_erp_table_name ON {SCHEMA}.erp_table (name);",
        
        "-- Index for table_id foreign key in erp_column",
        f"CREATE INDEX IF NOT EXISTS idx_erp_column_table_id_fk ON {SCHEMA}.erp_column (table_id);",
        
        "-- Update statistics to help query planner",
        f"ANALYZE {SCHEMA}.erp_column;",
        f"ANALYZE {SCHEMA}.erp_table;"
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
