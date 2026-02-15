#!/usr/bin/env python3
"""
Run this to see the full exception when connecting and querying the app schema.
Usage: python test_db_connection.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

def main():
    from database import engine
    from sqlalchemy import text

    print("Connecting and running SELECT 1 and SELECT from app.category (limit 1)...")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
            print("  SELECT 1: OK")
            conn.execute(text("SELECT id FROM app.category LIMIT 1"))
            conn.commit()
            print("  SELECT from app.category: OK")
    except Exception as e:
        print("Full exception:")
        import traceback
        traceback.print_exc()
        return 1
    print("Done.")
    return 0

if __name__ == "__main__":
    exit(main())
