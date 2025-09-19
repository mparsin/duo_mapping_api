# Exclude Column Functionality

This document describes the new "exclude" column functionality added to the Duo Mapping API.

## Overview

A new `exclude` column has been added to the `lines` table that allows individual lines to be excluded from all percentage calculations related to mapping. When `exclude=True`, the line will not be counted in the mapping completion percentages.

## Changes Made

### 1. Database Schema Changes

**File: `database.py`**
- Added `exclude = Column(Boolean, default=False, nullable=False)` to the `Lines` model

**File: `add_exclude_column.sql`**
- Migration script to add the exclude column to the database
- Sets default value to `FALSE` for backward compatibility
- Creates performance indexes for efficient querying

### 2. API Schema Updates

**File: `schemas.py`**
- Added `exclude` field to `LinesBase` schema (for input)
- Added `exclude` field to `Lines` schema (for responses)
- Added `exclude` field to `LineCreate` schema (for updates)
- Added `exclude` field to `LineResponse` schema (for update responses)

### 3. Business Logic Updates

**File: `main.py`**

#### Percentage Calculation Logic
- Updated `update_category_percent_mapped()` function to exclude lines where `exclude=True`
- **Total lines**: Lines with non-empty `field_name` AND `exclude=False`
- **Mapped lines**: Lines with both `table_id` and `column_id` AND non-empty `field_name` AND `exclude=False`

#### Schema Export Logic
- Updated `generate_mapped_schema()` function to exclude lines where `exclude=True`
- Excluded lines will not appear in the exported schema JSON

#### API Endpoints
- Updated `get_lines_by_category()` to include `exclude` field in response
- Updated `update_line()` to handle `exclude` field updates
- Added new `toggle_line_exclude()` endpoint for easy toggling

### 4. New API Endpoint

**Endpoint: `PATCH /api/lines/{line_id}/exclude`**
- Toggles the exclude status of a line
- Automatically recalculates category percentage after toggle
- Returns updated line information with new exclude status

## API Usage Examples

### 1. Get Lines with Exclude Status

```bash
GET /api/categories/1/lines
```

Response includes `exclude` field for each line:
```json
{
  "id": 1,
  "name": "Customer Name",
  "exclude": false,
  "table_id": 5,
  "column_id": 23,
  ...
}
```

### 2. Update Line with Exclude Field

```bash
PATCH /api/lines/1
Content-Type: application/json

{
  "exclude": true,
  "comment": "This line should be excluded from calculations"
}
```

### 3. Toggle Exclude Status

```bash
PATCH /api/lines/1/exclude
```

This will toggle the current exclude status and return the updated line.

### 4. Check Updated Percentages

```bash
GET /api/categories/1
```

The `percent_mapped` field will reflect the new calculation excluding the excluded lines.

## Database Migration

To apply the changes to your database, run the migration script:

```bash
psql -d your_database -f add_exclude_column.sql
```

Or execute the SQL commands directly in your database management tool.

## Performance Considerations

The migration script includes several indexes to optimize the new queries:

1. `idx_lines_exclude` - Index on the exclude column
2. `idx_lines_category_exclude_field_name` - Composite index for total lines calculation
3. `idx_lines_category_exclude_mapped` - Composite index for mapped lines calculation

These indexes ensure that the percentage calculation queries remain fast even with the additional filtering.

## Testing

Use the provided `test_exclude_functionality.py` script to test the new functionality:

```bash
python test_exclude_functionality.py
```

This script demonstrates:
- Getting categories and lines
- Toggling exclude status
- Updating lines with exclude field
- Checking updated percentages
- Testing schema export

## Backward Compatibility

- All existing functionality remains unchanged
- Default value for `exclude` is `FALSE`, so existing lines are not affected
- All existing API endpoints continue to work as before
- The new field is optional in all API requests

## Impact on Existing Data

- Existing lines will have `exclude=FALSE` by default
- No changes to existing percentage calculations until lines are explicitly excluded
- Schema exports will continue to include all existing mapped lines until they are excluded
