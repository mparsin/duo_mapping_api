#!/usr/bin/env python3
"""
Performance test for the find-table-matches endpoint
"""
import time
import requests
import json
from statistics import mean, median

def test_table_matching_performance(base_url="http://localhost:8000", iterations=3):
    """Test the performance of the find-table-matches endpoint"""
    
    url = f"{base_url}/api/find-table-matches"
    
    # Test cases with different column name lists
    test_cases = [
        {
            "name": "Small list (5 columns)",
            "column_names": ["customer_id", "customer_name", "email", "phone", "address"]
        },
        {
            "name": "Medium list (10 columns)", 
            "column_names": ["id", "name", "description", "type", "status", "created_date", "updated_date", "user_id", "category_id", "active"]
        },
        {
            "name": "Large list (20 columns)",
            "column_names": [
                "id", "name", "description", "type", "status", "created_date", "updated_date", 
                "user_id", "category_id", "active", "price", "quantity", "total", "discount",
                "tax", "shipping", "payment_method", "order_date", "delivery_date", "notes"
            ]
        },
        {
            "name": "Common columns (test-related)",
            "column_names": ["test", "testID", "testMethod", "testResult", "testStatus", "testDate", "testedBy"]
        }
    ]
    
    print("Testing find-table-matches endpoint performance")
    print("=" * 60)
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}")
        print(f"Columns: {len(test_case['column_names'])}")
        print("-" * 40)
        
        response_times = []
        
        for i in range(iterations):
            start_time = time.time()
            
            try:
                response = requests.post(
                    url, 
                    json={"column_names": test_case['column_names']},
                    timeout=30
                )
                end_time = time.time()
                
                response_time = end_time - start_time
                response_times.append(response_time)
                
                status = "✅" if response.status_code == 200 else "❌"
                result_count = len(response.json()) if response.status_code == 200 else 0
                
                print(f"  Iteration {i+1}: {status} {response_time:.3f}s - {result_count} table matches")
                
            except requests.exceptions.RequestException as e:
                print(f"  Iteration {i+1}: ❌ Error - {e}")
                continue
        
        if response_times:
            print(f"  Average: {mean(response_times):.3f}s")
            print(f"  Median:  {median(response_times):.3f}s")
            print(f"  Min:     {min(response_times):.3f}s")
            print(f"  Max:     {max(response_times):.3f}s")
        else:
            print("  No successful requests to analyze")

def test_specific_columns():
    """Test with specific column names that might be slow"""
    
    url = "http://localhost:8000/api/find-table-matches"
    
    # Test with a very common column name that might return many results
    test_data = {
        "column_names": ["id", "name", "description", "type", "status"]
    }
    
    print("\n" + "=" * 60)
    print("Testing with common column names (id, name, description, type, status)")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=test_data, timeout=60)
        end_time = time.time()
        
        response_time = end_time - start_time
        status = "✅" if response.status_code == 200 else "❌"
        result_count = len(response.json()) if response.status_code == 200 else 0
        
        print(f"Result: {status} {response_time:.3f}s - {result_count} table matches")
        
        if response.status_code == 200 and result_count > 0:
            # Show top 5 results
            results = response.json()
            print(f"\nTop 5 table matches:")
            for i, result in enumerate(results[:5], 1):
                print(f"  {i}. {result['table_name']} ({result['match_count']} matches)")
                print(f"     Matched columns: {', '.join(result['matched_columns'][:5])}{'...' if len(result['matched_columns']) > 5 else ''}")
        
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_table_matching_performance()
    test_specific_columns()
