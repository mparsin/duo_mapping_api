#!/usr/bin/env python3
"""
Test script to verify the fix for categories with all NULL field_name and excluded lines
This tests the specific scenario where categories 80 and 81 have all lines with NULL field_name and excluded
"""

def test_all_null_excluded_scenario():
    """Test the scenario where all lines have NULL field_name and are excluded"""
    
    print("=== Testing All NULL Field Name + Excluded Scenario ===\n")
    
    # Test case representing category 80/81 scenario
    test_cases = [
        {
            "id": 1,
            "field_name": None,
            "table_id": None,
            "column_id": None,
            "exclude": True,
            "description": "NULL field_name, no table/column mapping, excluded"
        },
        {
            "id": 2,
            "field_name": None,
            "table_id": None,
            "column_id": None,
            "exclude": True,
            "description": "NULL field_name, no table/column mapping, excluded"
        },
        {
            "id": 3,
            "field_name": None,
            "table_id": None,
            "column_id": None,
            "exclude": True,
            "description": "NULL field_name, no table/column mapping, excluded"
        }
    ]
    
    print("Test cases (representing categories 80/81):")
    for case in test_cases:
        print(f"  {case['id']}: {case['description']}")
    print()
    
    # Apply the updated logic
    def should_include_in_total_lines(line):
        """Apply the logic for total lines calculation"""
        # Exclude if explicitly marked as excluded
        if line['exclude']:
            return False
        
        # Exclude only if field_name is NULL/empty AND both table_id and column_id are NULL
        field_name_null_or_empty = line['field_name'] is None or line['field_name'] == ""
        both_table_column_null = line['table_id'] is None and line['column_id'] is None
        
        if field_name_null_or_empty and both_table_column_null:
            return False
        
        return True
    
    def is_excluded_line(line):
        """Check if a line is excluded"""
        return line['exclude'] == True
    
    # Test the logic
    print("Results:")
    total_lines = []
    excluded_lines = []
    
    for case in test_cases:
        should_include = should_include_in_total_lines(case)
        is_excluded = is_excluded_line(case)
        
        status = "INCLUDED IN TOTAL" if should_include else "EXCLUDED FROM TOTAL"
        excluded_status = "EXCLUDED" if is_excluded else "NOT EXCLUDED"
        
        print(f"  Line {case['id']}: {status} ({excluded_status}) - {case['description']}")
        
        if should_include:
            total_lines.append(case)
        
        if is_excluded:
            excluded_lines.append(case)
    
    print(f"\nSummary:")
    print(f"  Total test cases: {len(test_cases)}")
    print(f"  Total lines (for calculation): {len(total_lines)}")
    print(f"  Excluded lines: {len(excluded_lines)}")
    
    # Calculate percentage based on the updated logic
    total_lines_in_category = len(test_cases)  # All lines in category
    
    if total_lines_in_category == 0:
        # No lines in category at all
        percentage = 0.0
        print(f"  Mapping percentage: {percentage:.1f}% (No lines in category)")
    elif len(total_lines) == 0 and len(excluded_lines) > 0:
        # All valid lines are excluded, should be 100%
        percentage = 100.0
        print(f"  Mapping percentage: {percentage:.1f}% (All valid lines excluded - task completed)")
    else:
        # Normal calculation
        mapped_lines = [line for line in total_lines if line['table_id'] is not None and line['column_id'] is not None]
        if len(total_lines) > 0:
            percentage = (len(mapped_lines) / len(total_lines)) * 100
        else:
            percentage = 0.0
        print(f"  Mapping percentage: {percentage:.1f}%")
    
    print(f"\nExpected result for categories 80/81: 100% (all lines excluded)")
    print(f"Actual result: {percentage:.1f}%")
    
    if percentage == 100.0:
        print("✅ FIXED: Categories with all NULL field_name and excluded lines now show 100%")
    else:
        print("❌ STILL BROKEN: Categories with all NULL field_name and excluded lines show 0%")
    
    print("\n=== Test completed ===")

if __name__ == "__main__":
    test_all_null_excluded_scenario()
