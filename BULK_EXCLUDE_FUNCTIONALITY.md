# Bulk Exclude Functionality

This document describes the new bulk exclude functionality that allows excluding entire categories or subcategories with a single API call.

## Overview

Building on the individual line exclude functionality, the API now supports bulk operations to exclude or include entire categories and subcategories from percentage calculations with a single API call.

## New API Endpoints

### Category-Level Bulk Operations

#### Exclude Entire Category
```bash
PATCH /api/categories/{category_id}/exclude
```

**Description:** Excludes all lines in a category from percentage calculations by setting `exclude=True` for all lines in the category.

**Response:**
```json
{
  "category_id": 1,
  "category_name": "Customer Data",
  "lines_updated": 15,
  "exclude_status": true,
  "message": "Successfully excluded 15 lines from category 'Customer Data'"
}
```

#### Include Entire Category
```bash
PATCH /api/categories/{category_id}/include
```

**Description:** Includes all lines in a category in percentage calculations by setting `exclude=False` for all lines in the category.

**Response:**
```json
{
  "category_id": 1,
  "category_name": "Customer Data",
  "lines_updated": 15,
  "exclude_status": false,
  "message": "Successfully included 15 lines from category 'Customer Data'"
}
```

### Sub-Category-Level Bulk Operations

#### Exclude Entire Sub-Category
```bash
PATCH /api/categories/{category_id}/sub-categories/{sub_category_id}/exclude
```

**Description:** Excludes all lines in a sub-category from percentage calculations by setting `exclude=True` for all lines in the sub-category.

**Response:**
```json
{
  "category_id": 1,
  "category_name": "Customer Data",
  "sub_category_id": 1,
  "sub_category_name": "Personal Information",
  "lines_updated": 8,
  "exclude_status": true,
  "message": "Successfully excluded 8 lines from sub-category 'Personal Information'"
}
```

#### Include Entire Sub-Category
```bash
PATCH /api/categories/{category_id}/sub-categories/{sub_category_id}/include
```

**Description:** Includes all lines in a sub-category in percentage calculations by setting `exclude=False` for all lines in the sub-category.

**Response:**
```json
{
  "category_id": 1,
  "category_name": "Customer Data",
  "sub_category_id": 1,
  "sub_category_name": "Personal Information",
  "lines_updated": 8,
  "exclude_status": false,
  "message": "Successfully included 8 lines from sub-category 'Personal Information'"
}
```

## Key Features

### 1. **Automatic Percentage Recalculation**
- All bulk exclude/include operations automatically recalculate the parent category's `percent_mapped` field
- No need to call the recalculate endpoint separately

### 2. **Comprehensive Response Information**
- Returns the number of lines updated
- Includes category and sub-category names for clarity
- Provides clear success messages

### 3. **Error Handling**
- Returns 404 if category or sub-category doesn't exist
- Validates that sub-categories belong to the specified category

### 4. **Database Efficiency**
- Uses single UPDATE queries for bulk operations
- No need to fetch and update individual lines

## Use Cases

### 1. **Temporary Exclusion**
```bash
# Exclude a category temporarily while working on it
PATCH /api/categories/5/exclude

# Include it back when ready
PATCH /api/categories/5/include
```

### 2. **Sub-Category Management**
```bash
# Exclude a specific sub-category that's not relevant
PATCH /api/categories/1/sub-categories/3/exclude

# Include it back when needed
PATCH /api/categories/1/sub-categories/3/include
```

### 3. **Bulk Data Management**
```bash
# Exclude multiple categories at once
PATCH /api/categories/1/exclude
PATCH /api/categories/2/exclude
PATCH /api/categories/3/exclude

# Include them all back
PATCH /api/categories/1/include
PATCH /api/categories/2/include
PATCH /api/categories/3/include
```

## Testing

Use the provided test script to verify the functionality:

```bash
python test_bulk_exclude_functionality.py
```

This script demonstrates:
- Excluding and including entire categories
- Excluding and including entire sub-categories
- Checking updated percentages after each operation
- Error handling for non-existent categories/sub-categories

## Integration with Existing Functionality

### Individual Line Operations
- Individual line exclude operations still work as before
- Bulk operations work alongside individual operations
- You can mix individual and bulk operations as needed

### Percentage Calculations
- All percentage calculations automatically account for excluded lines
- Bulk operations immediately update percentages
- No manual recalculation needed

### Schema Export
- Excluded lines (whether excluded individually or via bulk operations) are excluded from schema export
- Consistent behavior across all exclude methods

## Performance Considerations

- Bulk operations use efficient database UPDATE queries
- No need to load individual line records into memory
- Automatic percentage recalculation is optimized with database indexes
- Suitable for categories with large numbers of lines

## Backward Compatibility

- All existing functionality remains unchanged
- New endpoints are additive and don't affect existing behavior
- Existing individual line operations continue to work as before
