#!/usr/bin/env python3
"""
ERP Insert Statement Generator

This script reads data from sandbox_template_v2.json and generates SQL INSERT statements
only for entries that don't already exist in the database. This ensures that existing
data is not duplicated while allowing new entries to be added.

Usage:
    python generate_erp_inserts.py [--dry-run] [--output-file OUTPUT_FILE]

Options:
    --dry-run: Show what would be inserted without actually executing
    --output-file: Save generated SQL to a file instead of printing to console
"""

import json
import os
import sys
import argparse
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database models
from database import Base, Category, SubCategory, ERPTable, ERPColumn, Lines

class ERPInsertGenerator:
    def __init__(self, database_url: str = None):
        """Initialize the generator with database connection."""
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/duo-mapping")
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.generated_sql = []
        self.stats = {
            'categories': {'new': 0, 'existing': 0},
            'sub_categories': {'new': 0, 'existing': 0},
            'erp_tables': {'new': 0, 'existing': 0},
            'erp_columns': {'new': 0, 'existing': 0},
            'lines': {'new': 0, 'existing': 0}
        }

    def load_template_data(self, template_file: str = "sandbox_template_v2.json") -> Dict[str, List[Dict]]:
        """Load data from the JSON template file and convert to ERP format."""
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            
            # Convert the schema format to our ERP format
            return self.convert_schema_to_erp_format(raw_data)
        except FileNotFoundError:
            print(f"Error: Template file '{template_file}' not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in template file: {e}")
            sys.exit(1)

    def convert_schema_to_erp_format(self, raw_data: Dict) -> Dict[str, List[Dict]]:
        """Convert the schema format to ERP format for processing."""
        erp_data = {
            'categories': [],
            'sub_categories': [],
            'erp_tables': [],
            'erp_columns': [],
            'lines': []
        }
        
        # Extract tables and columns from schemas
        if 'schemas' in raw_data:
            print(f"Found {len(raw_data['schemas'])} schemas")
            for schema in raw_data['schemas']:
                if 'tables' in schema:
                    print(f"Found {len(schema['tables'])} tables in schema '{schema.get('name', 'unknown')}'")
                    for table in schema['tables']:
                        # Add ERP table
                        erp_table = {
                            'name': table['name'],
                            'description': table.get('description', '')
                        }
                        erp_data['erp_tables'].append(erp_table)
                        
                        # Add ERP columns for this table
                        if 'columns' in table:
                            table_id = len(erp_data['erp_tables'])  # Current table ID
                            for column in table['columns']:
                                erp_column = {
                                    'name': column['name'],
                                    'comment': column.get('comment', ''),
                                    'type': column.get('type', ''),
                                    'table_id': table_id
                                }
                                erp_data['erp_columns'].append(erp_column)
                else:
                    print("No tables found in schema")
        else:
            print("No schemas found in data")
        
        # Create some sample categories and sub-categories for demonstration
        erp_data['categories'] = [
            {'name': 'Database Tables', 'description': 'Tables from the database schema'},
            {'name': 'System Tables', 'description': 'System and configuration tables'},
            {'name': 'Business Tables', 'description': 'Business logic tables'}
        ]
        
        erp_data['sub_categories'] = [
            {'name': 'Core Tables', 'category_id': 1},
            {'name': 'Reference Tables', 'category_id': 1},
            {'name': 'System Configuration', 'category_id': 2},
            {'name': 'User Management', 'category_id': 2},
            {'name': 'Transaction Tables', 'category_id': 3},
            {'name': 'Master Data', 'category_id': 3}
        ]
        
        # Create sample lines for some tables and columns
        sample_lines = []
        column_counter = 1
        
        for i, table in enumerate(erp_data['erp_tables'][:20], 1):  # Limit to first 20 tables
            table_columns = [col for col in erp_data['erp_columns'] if col['table_id'] == i]
            for j, column in enumerate(table_columns[:3], 1):  # Limit to first 3 columns per table
                line = {
                    'categoryid': 1 if i <= 7 else 2 if i <= 14 else 3,
                    'default': 'N/A',
                    'customer_settings': 'Required',
                    'no_of_chars': '50',
                    'field_name': f"{table['name']}_{column['name']}",
                    'reason': f"Field from {table['name']} table",
                    'name': f"{table['name']} - {column['name']}",
                    'sub_category_id': 1 if i <= 7 else 2 if i <= 14 else 3,
                    'table_id': i,
                    'column_id': column_counter
                }
                sample_lines.append(line)
                column_counter += 1
        
        erp_data['lines'] = sample_lines
        
        print(f"Converted to ERP format: {len(erp_data['erp_tables'])} tables, {len(erp_data['erp_columns'])} columns")
        
        return erp_data

    def check_category_exists(self, session, name: str) -> Optional[int]:
        """Check if a category with the given name already exists."""
        category = session.query(Category).filter(Category.Name == name).first()
        return category.id if category else None

    def check_sub_category_exists(self, session, name: str, category_id: int) -> Optional[int]:
        """Check if a sub-category with the given name and category_id already exists."""
        sub_category = session.query(SubCategory).filter(
            SubCategory.name == name,
            SubCategory.category_id == category_id
        ).first()
        return sub_category.id if sub_category else None

    def check_erp_table_exists(self, session, name: str) -> Optional[int]:
        """Check if an ERP table with the given name already exists."""
        erp_table = session.query(ERPTable).filter(ERPTable.name == name).first()
        return erp_table.id if erp_table else None

    def check_erp_column_exists(self, session, name: str, table_id: int) -> Optional[int]:
        """Check if an ERP column with the given name and table_id already exists."""
        erp_column = session.query(ERPColumn).filter(
            ERPColumn.name == name,
            ERPColumn.table_id == table_id
        ).first()
        return erp_column.id if erp_column else None

    def check_line_exists(self, session, line_data: Dict) -> Optional[int]:
        """Check if a line with the same characteristics already exists."""
        # Check for lines with same categoryid, name, and field_name
        line = session.query(Lines).filter(
            Lines.categoryid == line_data['categoryid'],
            Lines.name == line_data['name'],
            Lines.field_name == line_data['field_name']
        ).first()
        return line.id if line else None

    def generate_category_inserts(self, session, categories: List[Dict]) -> List[str]:
        """Generate INSERT statements for categories that don't exist."""
        sql_statements = []
        
        for category in categories:
            existing_id = self.check_category_exists(session, category['name'])
            if existing_id:
                self.stats['categories']['existing'] += 1
                print(f"Category '{category['name']}' already exists (ID: {existing_id})")
            else:
                self.stats['categories']['new'] += 1
                sql = f"INSERT INTO category (\"Name\") VALUES ('{category['name']}');"
                sql_statements.append(sql)
                self.generated_sql.append(sql)
                print(f"New category: '{category['name']}'")
        
        return sql_statements

    def generate_sub_category_inserts(self, session, sub_categories: List[Dict]) -> List[str]:
        """Generate INSERT statements for sub-categories that don't exist."""
        sql_statements = []
        
        for sub_category in sub_categories:
            existing_id = self.check_sub_category_exists(session, sub_category['name'], sub_category['category_id'])
            if existing_id:
                self.stats['sub_categories']['existing'] += 1
                print(f"Sub-category '{sub_category['name']}' already exists (ID: {existing_id})")
            else:
                self.stats['sub_categories']['new'] += 1
                sql = f"INSERT INTO \"sub-category\" (name, category_id) VALUES ('{sub_category['name']}', {sub_category['category_id']});"
                sql_statements.append(sql)
                self.generated_sql.append(sql)
                print(f"New sub-category: '{sub_category['name']}'")
        
        return sql_statements

    def generate_erp_table_inserts(self, session, erp_tables: List[Dict]) -> List[str]:
        """Generate INSERT statements for ERP tables that don't exist."""
        sql_statements = []
        
        for erp_table in erp_tables:
            existing_id = self.check_erp_table_exists(session, erp_table['name'])
            if existing_id:
                self.stats['erp_tables']['existing'] += 1
                print(f"ERP table '{erp_table['name']}' already exists (ID: {existing_id})")
            else:
                self.stats['erp_tables']['new'] += 1
                description = erp_table.get('description', '').replace("'", "''")
                sql = f"INSERT INTO erp_table (name, description) VALUES ('{erp_table['name']}', '{description}');"
                sql_statements.append(sql)
                self.generated_sql.append(sql)
                print(f"New ERP table: '{erp_table['name']}'")
        
        return sql_statements

    def generate_erp_column_inserts(self, session, erp_columns: List[Dict]) -> List[str]:
        """Generate INSERT statements for ERP columns that don't exist."""
        sql_statements = []
        
        for erp_column in erp_columns:
            existing_id = self.check_erp_column_exists(session, erp_column['name'], erp_column['table_id'])
            if existing_id:
                self.stats['erp_columns']['existing'] += 1
                print(f"ERP column '{erp_column['name']}' already exists (ID: {existing_id})")
            else:
                self.stats['erp_columns']['new'] += 1
                comment = erp_column.get('comment') or ''
                comment = comment.replace("'", "''") if comment else ''
                column_type = erp_column.get('type') or ''
                column_type = column_type.replace("'", "''") if column_type else ''
                sql = f"INSERT INTO erp_column (name, comment, type, table_id) VALUES ('{erp_column['name']}', '{comment}', '{column_type}', {erp_column['table_id']});"
                sql_statements.append(sql)
                self.generated_sql.append(sql)
                print(f"New ERP column: '{erp_column['name']}'")
        
        return sql_statements

    def generate_line_inserts(self, session, lines: List[Dict]) -> List[str]:
        """Generate INSERT statements for lines that don't exist."""
        sql_statements = []
        
        for line in lines:
            existing_id = self.check_line_exists(session, line)
            if existing_id:
                self.stats['lines']['existing'] += 1
                print(f"Line '{line['name']}' already exists (ID: {existing_id})")
            else:
                self.stats['lines']['new'] += 1
                # Handle None values for optional fields
                default = line.get('default', '').replace("'", "''") if line.get('default') else 'NULL'
                customer_settings = line.get('customer_settings', '').replace("'", "''") if line.get('customer_settings') else 'NULL'
                no_of_chars = line.get('no_of_chars', '').replace("'", "''") if line.get('no_of_chars') else 'NULL'
                field_name = line.get('field_name', '').replace("'", "''") if line.get('field_name') else 'NULL'
                reason = line.get('reason', '').replace("'", "''") if line.get('reason') else 'NULL'
                sub_category_id = line.get('sub_category_id') if line.get('sub_category_id') else 'NULL'
                table_id = line.get('table_id') if line.get('table_id') else 'NULL'
                column_id = line.get('column_id') if line.get('column_id') else 'NULL'
                
                sql = f"""INSERT INTO lines (categoryid, default, customer_settings, no_of_chars, field_name, reason, name, sub_category_id, table_id, column_id) 
VALUES ({line['categoryid']}, '{default}', '{customer_settings}', '{no_of_chars}', '{field_name}', '{reason}', '{line['name']}', {sub_category_id}, {table_id}, {column_id});"""
                sql_statements.append(sql)
                self.generated_sql.append(sql)
                print(f"New line: '{line['name']}'")
        
        return sql_statements

    def generate_all_inserts(self, template_file: str = "sandbox_template_v2.json", dry_run: bool = False) -> List[str]:
        """Generate all INSERT statements for new entries."""
        print(f"Loading template data from {template_file}...")
        template_data = self.load_template_data(template_file)
        
        print("Checking existing data in database...")
        session = self.SessionLocal()
        
        try:
            all_sql = []
            
            # Generate inserts for each table type
            if 'categories' in template_data:
                print("\n=== Processing Categories ===")
                all_sql.extend(self.generate_category_inserts(session, template_data['categories']))
            
            if 'sub_categories' in template_data:
                print("\n=== Processing Sub-Categories ===")
                all_sql.extend(self.generate_sub_category_inserts(session, template_data['sub_categories']))
            
            if 'erp_tables' in template_data:
                print("\n=== Processing ERP Tables ===")
                all_sql.extend(self.generate_erp_table_inserts(session, template_data['erp_tables']))
            
            if 'erp_columns' in template_data:
                print("\n=== Processing ERP Columns ===")
                all_sql.extend(self.generate_erp_column_inserts(session, template_data['erp_columns']))
            
            if 'lines' in template_data:
                print("\n=== Processing Lines ===")
                all_sql.extend(self.generate_line_inserts(session, template_data['lines']))
            
            return all_sql
            
        finally:
            session.close()

    def print_statistics(self):
        """Print summary statistics."""
        print("\n" + "="*50)
        print("SUMMARY STATISTICS")
        print("="*50)
        
        total_new = 0
        total_existing = 0
        
        for table_type, stats in self.stats.items():
            new_count = stats['new']
            existing_count = stats['existing']
            total_new += new_count
            total_existing += existing_count
            
            print(f"{table_type.replace('_', ' ').title()}: {new_count} new, {existing_count} existing")
        
        print("-" * 50)
        print(f"Total: {total_new} new entries, {total_existing} existing entries")
        print(f"Generated {len(self.generated_sql)} SQL statements")

def main():
    parser = argparse.ArgumentParser(description='Generate ERP INSERT statements from JSON template')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be inserted without executing')
    parser.add_argument('--output-file', type=str, help='Save generated SQL to file instead of printing to console')
    parser.add_argument('--template-file', type=str, default='sandbox_template_v2.json', help='Path to JSON template file')
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = ERPInsertGenerator()
    
    # Generate SQL statements
    sql_statements = generator.generate_all_inserts(args.template_file, args.dry_run)
    
    # Print statistics
    generator.print_statistics()
    
    if sql_statements:
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write("-- Generated ERP INSERT statements\n")
                from datetime import datetime
                f.write("-- Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
                for sql in sql_statements:
                    f.write(sql + "\n")
            print(f"\nSQL statements saved to: {args.output_file}")
        else:
            print("\n" + "="*50)
            print("GENERATED SQL STATEMENTS")
            print("="*50)
            for sql in sql_statements:
                print(sql)
    else:
        print("\nNo new entries to insert. All data already exists in the database.")

if __name__ == "__main__":
    main()
