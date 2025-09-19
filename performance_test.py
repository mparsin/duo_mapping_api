#!/usr/bin/env python3
"""
Performance test for the search_columns endpoint
"""
import time
import requests
from statistics import mean, median

def test_endpoint_performance(base_url="http://localhost:8000", search_term="test", iterations=5):
    """Test the performance of the search_columns endpoint"""
    
    url = f"{base_url}/api/search-columns"
    params = {"columnName": search_term}
    
    print(f"Testing search_columns endpoint with term '{search_term}'")
    print(f"Running {iterations} iterations...")
    print("-" * 50)
    
    response_times = []
    
    for i in range(iterations):
        start_time = time.time()
        
        try:
            response = requests.get(url, params=params, timeout=30)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            status = "✅" if response.status_code == 200 else "❌"
            result_count = len(response.json()) if response.status_code == 200 else 0
            
            print(f"Iteration {i+1}: {status} {response_time:.3f}s - {result_count} results")
            
        except requests.exceptions.RequestException as e:
            print(f"Iteration {i+1}: ❌ Error - {e}")
            continue
    
    if response_times:
        print("-" * 50)
        print(f"Performance Summary:")
        print(f"  Average: {mean(response_times):.3f}s")
        print(f"  Median:  {median(response_times):.3f}s")
        print(f"  Min:     {min(response_times):.3f}s")
        print(f"  Max:     {max(response_times):.3f}s")
        print(f"  Total:   {sum(response_times):.3f}s")
    else:
        print("No successful requests to analyze")

if __name__ == "__main__":
    # Test with different search terms
    test_terms = ["test", "customer", "order", "id"]
    
    for term in test_terms:
        print(f"\n{'='*60}")
        test_endpoint_performance(search_term=term, iterations=3)
        time.sleep(1)  # Brief pause between tests


