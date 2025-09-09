# ERP Insert Statement Generator

This tool generates SQL INSERT statements from a JSON template file, ensuring that only new entries are added to the database without duplicating existing data.

## Files Created

- `sandbox_template_v2.json` - JSON template file containing sample ERP data
- `generate_erp_inserts.py` - Main script for generating INSERT statements
- `README_generate_erp_inserts.md` - This documentation file

## Features

- **Duplicate Prevention**: Checks existing database entries before generating INSERT statements
- **Comprehensive Coverage**: Handles all database tables (categories, sub-categories, ERP tables, ERP columns, lines)
- **Flexible Output**: Can display to console or save to file
- **Dry Run Mode**: Preview what would be inserted without executing
- **Statistics Tracking**: Shows counts of new vs existing entries
- **Error Handling**: Proper validation and error reporting

## Usage

### Basic Usage

```bash
# Generate INSERT statements and display to console
python generate_erp_inserts.py

# Dry run - show what would be inserted without executing
python generate_erp_inserts.py --dry-run

# Save output to a file
python generate_erp_inserts.py --output-file my_inserts.sql

# Use a different template file
python generate_erp_inserts.py --template-file my_template.json
```

### Command Line Options

- `--dry-run`: Show what would be inserted without actually executing
- `--output-file FILE`: Save generated SQL to a file instead of printing to console
- `--template-file FILE`: Path to JSON template file (default: sandbox_template_v2.json)

### Example Output

```
Loading template data from sandbox_template_v2.json...
Checking existing data in database...

=== Processing Categories ===
New category: 'Customer Information'
New category: 'Product Data'
New category: 'Order Management'

=== Processing Sub-Categories ===
New sub-category: 'Personal Details'
...

==================================================
SUMMARY STATISTICS
==================================================
Categories: 3 new, 0 existing
Sub Categories: 6 new, 0 existing
Erp Tables: 5 new, 0 existing
Erp Columns: 17 new, 0 existing
Lines: 10 new, 0 existing
--------------------------------------------------
Total: 41 new entries, 0 existing entries
Generated 41 SQL statements
```

## JSON Template Structure

The `sandbox_template_v2.json` file should contain the following structure:

```json
{
  "categories": [
    {
      "name": "Category Name",
      "description": "Optional description"
    }
  ],
  "sub_categories": [
    {
      "name": "Sub-category Name",
      "category_id": 1
    }
  ],
  "erp_tables": [
    {
      "name": "table_name",
      "description": "Table description"
    }
  ],
  "erp_columns": [
    {
      "name": "column_name",
      "comment": "Column description",
      "type": "VARCHAR(100)",
      "table_id": 1
    }
  ],
  "lines": [
    {
      "categoryid": 1,
      "default": "Default value",
      "customer_settings": "Required/Optional",
      "no_of_chars": "50",
      "field_name": "field_name",
      "reason": "Field purpose",
      "name": "Display Name",
      "sub_category_id": 1,
      "table_id": 1,
      "column_id": 1
    }
  ]
}
```

## Database Checking Logic

The script checks for existing entries using the following criteria:

- **Categories**: By name
- **Sub-categories**: By name and category_id
- **ERP Tables**: By name
- **ERP Columns**: By name and table_id
- **Lines**: By categoryid, name, and field_name

## Dependencies

- Python 3.7+
- SQLAlchemy
- psycopg2-binary (for PostgreSQL)
- python-dotenv

Install dependencies with:
```bash
pip install sqlalchemy psycopg2-binary python-dotenv
```

## Environment Configuration

The script uses the `DATABASE_URL` environment variable. Set it in your `.env` file:

```
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

## Error Handling

The script includes comprehensive error handling for:
- Missing template files
- Invalid JSON format
- Database connection issues
- SQL generation errors

## Security Notes

- SQL injection protection through parameterized queries
- Input validation and sanitization
- Safe handling of special characters in data







