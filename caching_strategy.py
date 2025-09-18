"""
Caching strategy for the Duo Mapping API
This file contains caching utilities that can be integrated into the main API
"""

from functools import lru_cache
from typing import Dict, List, Tuple
import time
from sqlalchemy.orm import Session
from database import ERPColumn, ERPTable, Category, Lines
from schemas import CategoryMappingInfo, ColumnSearchResult
from sqlalchemy import func

class ColumnSearchCache:
    """
    Simple in-memory cache for column search results
    """
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default TTL
        self.cache: Dict[str, Tuple[List[ColumnSearchResult], float]] = {}
        self.ttl = ttl_seconds
    
    def get(self, search_term: str) -> List[ColumnSearchResult] | None:
        """Get cached results if they exist and are not expired"""
        if search_term in self.cache:
            results, timestamp = self.cache[search_term]
            if time.time() - timestamp < self.ttl:
                return results
            else:
                # Remove expired entry
                del self.cache[search_term]
        return None
    
    def set(self, search_term: str, results: List[ColumnSearchResult]):
        """Cache the results with current timestamp"""
        self.cache[search_term] = (results, time.time())
    
    def clear(self):
        """Clear all cached entries"""
        self.cache.clear()
    
    def size(self) -> int:
        """Get number of cached entries"""
        return len(self.cache)

# Global cache instance
column_search_cache = ColumnSearchCache()

@lru_cache(maxsize=1000)
def get_cached_category_mappings(column_ids_tuple: Tuple[int, ...]) -> Dict[int, List[CategoryMappingInfo]]:
    """
    Cached function to get category mappings for a list of column IDs
    This uses LRU cache to avoid repeated database queries for the same column sets
    """
    # This would need to be called with a database session
    # For now, this is a placeholder showing the caching pattern
    pass

def clear_all_caches():
    """Clear all caches - useful for testing or when data changes"""
    column_search_cache.clear()
    get_cached_category_mappings.cache_clear()

# Example usage in the main endpoint:
"""
def search_columns_with_cache(columnName: str, db: Session = Depends(get_db)):
    search_term = columnName.strip().lower()
    
    # Check cache first
    cached_results = column_search_cache.get(search_term)
    if cached_results is not None:
        return cached_results
    
    # If not in cache, perform the search
    results = perform_optimized_search(search_term, db)
    
    # Cache the results
    column_search_cache.set(search_term, results)
    
    return results
"""
