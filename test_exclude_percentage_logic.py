#!/usr/bin/env python3
"""
Test script to verify the corrected percentage calculation logic
This script tests that when all lines in a category are excluded, the percentage is 100%
"""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def test_exclude_percentage_logic():
    """Test the corrected percentage calculation logic"""
    
    print("=== Testing Exclude Percentage Logic ===\n")
    
    # Test 1: Get initial state
    print("1. Getting initial categories...")
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
        included_count = len(lines) - excluded_count
        print(f"  - Currently excluded: {excluded_count}")
        print(f"  - Currently included: {included_count}")
    else:
        print(f"Error getting lines: {response.status_code}")
        return
    
    print()
    
    # Test 3: Check current category percentage
    print("3. Checking current category percentage...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
        return
    
    print()
    
    # Test 4: Exclude all lines in the category
    print("4. Excluding all lines in category 1...")
    response = requests.patch(f"{BASE_URL}/categories/1/exclude")
    if response.status_code == 200:
        result = response.json()
        print(f"  - Lines updated: {result['lines_updated']}")
        print(f"  - Message: {result['message']}")
    else:
        print(f"Error excluding category: {response.status_code}")
        return
    
    print()
    
    # Test 5: Check category percentage after excluding all lines
    print("5. Checking category percentage after excluding all lines...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
        if category['percent_mapped'] == 100.0:
            print("  ✅ CORRECT: Percentage is 100% when all lines are excluded")
        else:
            print(f"  ❌ INCORRECT: Expected 100%, got {category['percent_mapped']}%")
    else:
        print(f"Error getting category: {response.status_code}")
        return
    
    print()
    
    # Test 6: Include all lines back
    print("6. Including all lines back in category 1...")
    response = requests.patch(f"{BASE_URL}/categories/1/include")
    if response.status_code == 200:
        result = response.json()
        print(f"  - Lines updated: {result['lines_updated']}")
        print(f"  - Message: {result['message']}")
    else:
        print(f"Error including category: {response.status_code}")
        return
    
    print()
    
    # Test 7: Check category percentage after including all lines
    print("7. Checking category percentage after including all lines...")
    response = requests.get(f"{BASE_URL}/categories/1")
    if response.status_code == 200:
        category = response.json()
        print(f"  - Category 1 percentage: {category['percent_mapped']}%")
        print("  - This should now show the normal mapping percentage")
    else:
        print(f"Error getting category: {response.status_code}")
        return
    
    print()
    
    # Test 8: Test individual line exclusion to verify the logic
    print("8. Testing individual line exclusion logic...")
    response = requests.get(f"{BASE_URL}/categories/1/lines")
    if response.status_code == 200:
        lines = response.json()
        if lines:
            # Exclude the first line
            line_id = lines[0]['id']
            print(f"  - Excluding individual line {line_id}...")
            response = requests.patch(f"{BASE_URL}/lines/{line_id}/exclude")
            if response.status_code == 200:
                result = response.json()
                print(f"  - Line {line_id} exclude status: {result['exclude']}")
                
                # Check category percentage
                response = requests.get(f"{BASE_URL}/categories/1")
                if response.status_code == 200:
                    category = response.json()
                    print(f"  - Category 1 percentage after excluding one line: {category['percent_mapped']}%")
            else:
                print(f"  Error excluding line: {response.status_code}")
        else:
            print("  No lines found to test individual exclusion")
    else:
        print(f"Error getting lines: {response.status_code}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_exclude_percentage_logic()
