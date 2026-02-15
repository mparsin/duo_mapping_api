#!/usr/bin/env python3
"""
Safely create performance indexes for the Duo Mapping API.
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

def create_indexes():
    """Create all performance indexes safely"""
    
    indexes = [
        "-- Index for case-insensitive column name searches",
        f"CREATE INDEX IF NOT EXISTS idx_erp_column_name_lower ON {SCHEMA}.erp_column (LOWER(name));",
        
        "-- Index for column_id lookups in lines table",
        f"CREATE INDEX IF NOT EXISTS idx_lines_column_id ON {SCHEMA}.lines (column_id);",
        
        "-- Index for categoryid lookups in lines table", 
        f"CREATE INDEX IF NOT EXISTS idx_lines_categoryid ON {SCHEMA}.lines (categoryid);",
        
        "-- Composite index for the category mapping query",
        f"CREATE INDEX IF NOT EXISTS idx_lines_column_category ON {SCHEMA}.lines (column_id, categoryid);",
        
        "-- Index for table_id lookups in erp_column table",
        f"CREATE INDEX IF NOT EXISTS idx_erp_column_table_id ON {SCHEMA}.erp_column (table_id);",
        
        "-- Index for category name lookups (using correct column name)",
        f"CREATE INDEX IF NOT EXISTS idx_category_name ON {SCHEMA}.category (\"Name\");",
        
        "-- Partial index for non-null column_id values",
        f"CREATE INDEX IF NOT EXISTS idx_lines_column_id_not_null ON {SCHEMA}.lines (column_id) WHERE column_id IS NOT NULL;",
        
        "-- Index for category ID lookups",
        f"CREATE INDEX IF NOT EXISTS idx_category_id ON {SCHEMA}.category (id);",
        
        "-- Index for table ID lookups",
        f"CREATE INDEX IF NOT EXISTS idx_erp_table_id ON {SCHEMA}.erp_table (id);",
        
        "-- Additional foreign key indexes",
        f"CREATE INDEX IF NOT EXISTS idx_lines_table_id ON {SCHEMA}.lines (table_id);",
        f"CREATE INDEX IF NOT EXISTS idx_lines_sub_category_id ON {SCHEMA}.lines (sub_category_id);"
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
