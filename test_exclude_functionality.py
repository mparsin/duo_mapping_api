#!/usr/bin/env python3
"""
Test script to demonstrate the new exclude functionality
This script shows how to use the new exclude column feature
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_exclude_functionality():
    """Test the exclude functionality"""
    
    print("=== Testing Exclude Functionality ===\n")
    
    # Test 1: Get categories to see current percentages
    print("1. Getting current categories...")
    response = requests.get(f"{BASE_URL}/categories")
    if response.status_code == 200:
        categories = response.json()
        print(f"Found {len(categories)} categories")
        for cat in categories[:3]:  # Show first 3
            print(f"  - {cat['Name']}: {cat['percent_mapped']}% mapped")
    else:
        print(f"Error getting categories: {response.status_code}")
        return
    
    print()
    
    # Test 2: Get lines for a specific category
    print("2. Getting lines for category 1...")
    response = requests.get(f"{BASE_URL}/categories/1/lines")
    if response.status_code == 200:
        lines = response.json()
        print(f"Found {len(lines)} lines in category 1")
        for line in lines[:3]:  # Show first 3
            print(f"  - Line {line['id']}: {line['name']} (exclude: {line['exclude']})")
    else:
        print(f"Error getting lines: {response.status_code}")
        return
    
    print()
    
    # Test 3: Toggle exclude status for a line
    if lines:
        line_id = lines[0]['id']
        print(f"3. Toggling exclude status for line {line_id}...")
        response = requests.patch(f"{BASE_URL}/lines/{line_id}/exclude")
        if response.status_code == 200:
            result = response.json()
            print(f"  - Line {line_id} exclude status: {result['exclude']}")
            print(f"  - Action: {result['action']}")
        else:
            print(f"Error toggling exclude: {response.status_code}")
            return
    
    print()
    
    # Test 4: Check updated category percentage
    print("4. Checking updated category percentage...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
    
    print()
    
    # Test 5: Update line with exclude field
    if lines:
        line_id = lines[0]['id']
        print(f"5. Updating line {line_id} with exclude field...")
        update_data = {
            "exclude": True,
            "comment": "Updated via API test"
        }
        response = requests.patch(f"{BASE_URL}/lines/{line_id}", json=update_data)
        if response.status_code == 200:
            result = response.json()
            print(f"  - Line {line_id} exclude status: {result['exclude']}")
            print(f"  - Comment: {result['comment']}")
            print(f"  - Action: {result['action']}")
        else:
            print(f"Error updating line: {response.status_code}")
    
    print()
    
    # Test 6: Test schema export (should exclude lines with exclude=True)
    print("6. Testing schema export (should exclude lines with exclude=True)...")
    response = requests.get(f"{BASE_URL}/download-schema")
    if response.status_code == 200:
        schema = response.json()
        print(f"  - Schema contains {schema['total_tables']} tables")
        print(f"  - Schema contains {schema['total_mapped_columns']} mapped columns")
        print(f"  - Generated at: {schema['generated_at']}")
    else:
        print(f"Error getting schema: {response.status_code}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_exclude_functionality()

