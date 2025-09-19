#!/usr/bin/env python3
"""
Test script to demonstrate the new bulk exclude functionality
This script shows how to use the new bulk exclude endpoints for categories and subcategories
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_bulk_exclude_functionality():
    """Test the bulk exclude functionality"""
    
    print("=== Testing Bulk Exclude Functionality ===\n")
    
    # Test 1: Get initial state
    print("1. Getting initial categories and lines...")
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
        excluded_count = sum(1 for line in lines if line['exclude'])
        print(f"  - Currently excluded: {excluded_count}")
        print(f"  - Currently included: {len(lines) - excluded_count}")
    else:
        print(f"Error getting lines: {response.status_code}")
        return
    
    print()
    
    # Test 3: Exclude entire category
    print("3. Excluding entire category 1...")
    response = requests.patch(f"{BASE_URL}/categories/1/exclude")
    if response.status_code == 200:
        result = response.json()
        print(f"  - Category: {result['category_name']}")
        print(f"  - Lines updated: {result['lines_updated']}")
        print(f"  - Exclude status: {result['exclude_status']}")
        print(f"  - Message: {result['message']}")
    else:
        print(f"Error excluding category: {response.status_code}")
        return
    
    print()
    
    # Test 4: Check updated category percentage
    print("4. Checking updated category percentage...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}% (should be 0%)")
    else:
        print(f"Error getting category: {response.status_code}")
    
    print()
    
    # Test 5: Include entire category
    print("5. Including entire category 1...")
    response = requests.patch(f"{BASE_URL}/categories/1/include")
    if response.status_code == 200:
        result = response.json()
        print(f"  - Category: {result['category_name']}")
        print(f"  - Lines updated: {result['lines_updated']}")
        print(f"  - Exclude status: {result['exclude_status']}")
        print(f"  - Message: {result['message']}")
    else:
        print(f"Error including category: {response.status_code}")
    
    print()
    
    # Test 6: Check updated category percentage after include
    print("6. Checking updated category percentage after include...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
    
    print()
    
    # Test 7: Get sub-categories for category 1
    print("7. Getting sub-categories for category 1...")
    response = requests.get(f"{BASE_URL}/categories/1/sub-categories")
    if response.status_code == 200:
        sub_categories = response.json()
        print(f"Found {len(sub_categories)} sub-categories in category 1")
        for sub_cat in sub_categories[:3]:  # Show first 3
            print(f"  - {sub_cat['name']} (ID: {sub_cat['id']})")
    else:
        print(f"Error getting sub-categories: {response.status_code}")
        return
    
    print()
    
    # Test 8: Exclude entire sub-category (if any exist)
    if sub_categories:
        sub_category_id = sub_categories[0]['id']
        print(f"8. Excluding entire sub-category {sub_category_id}...")
        response = requests.patch(f"{BASE_URL}/categories/1/sub-categories/{sub_category_id}/exclude")
        if response.status_code == 200:
            result = response.json()
            print(f"  - Category: {result['category_name']}")
            print(f"  - Sub-category: {result['sub_category_name']}")
            print(f"  - Lines updated: {result['lines_updated']}")
            print(f"  - Exclude status: {result['exclude_status']}")
            print(f"  - Message: {result['message']}")
        else:
            print(f"Error excluding sub-category: {response.status_code}")
    else:
        print("8. No sub-categories found to test")
    
    print()
    
    # Test 9: Check updated category percentage after sub-category exclude
    print("9. Checking updated category percentage after sub-category exclude...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
    
    print()
    
    # Test 10: Include entire sub-category
    if sub_categories:
        print(f"10. Including entire sub-category {sub_category_id}...")
        response = requests.patch(f"{BASE_URL}/categories/1/sub-categories/{sub_category_id}/include")
        if response.status_code == 200:
            result = response.json()
            print(f"  - Category: {result['category_name']}")
            print(f"  - Sub-category: {result['sub_category_name']}")
            print(f"  - Lines updated: {result['lines_updated']}")
            print(f"  - Exclude status: {result['exclude_status']}")
            print(f"  - Message: {result['message']}")
        else:
            print(f"Error including sub-category: {response.status_code}")
    else:
        print("10. No sub-categories found to test")
    
    print()
    
    # Test 11: Final state check
    print("11. Final state check...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_bulk_exclude_functionality()
