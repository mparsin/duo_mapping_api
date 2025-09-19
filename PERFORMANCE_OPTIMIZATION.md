# Performance Optimization Guide for Search Columns Endpoint

## Problem Analysis

The original `/search-columns` endpoint was taking 10+ seconds due to several performance bottlenecks:

1. **N+1 Query Problem**: Made a separate database query for each matching column to get category mappings
2. **Loading All Data**: Loaded ALL columns and tables into memory, then filtered in Python
3. **No Database Indexes**: Search was done in Python instead of using database indexes
4. **Inefficient Filtering**: Used Python string operations instead of database-level filtering

## Optimizations Implemented

### 1. Database Query Optimization

**Before:**
```python
# Load ALL columns first
columns = db.query(ERPColumn, ERPTable).join(ERPTable, ERPColumn.table_id == ERPTable.id).all()

# Then filter in Python
for column, table in columns:
    if column.name.lower() == search_term:
        # Make separate query for each match
        mapped_categories = db.query(Category.id, Category.Name)...
```

**After:**
```python
# Use database-level filtering with indexes
exact_columns = db.query(ERPColumn, ERPTable).join(
    ERPTable, ERPColumn.table_id == ERPTable.id
).filter(
    func.lower(ERPColumn.name) == search_term
).all()

# Single query for all category mappings
mappings = db.query(
    Lines.column_id, Category.id, Category.Name
).join(
    Category, Lines.categoryid == Category.id
).filter(
    Lines.column_id.in_(all_matched_column_ids)
).distinct().all()
```

### 2. Database Indexes

Run the following SQL script to add performance indexes:

```sql
-- See add_performance_indexes.sql for the complete script
CREATE INDEX IF NOT EXISTS idx_erp_column_name_lower 
ON erp_column (LOWER(name));

CREATE INDEX IF NOT EXISTS idx_lines_column_id 
ON lines (column_id);

CREATE INDEX IF NOT EXISTS idx_lines_categoryid 
ON lines (categoryid);
```

### 3. Query Reduction

- **Before**: 1 query to load all columns + N queries for category mappings = 1 + N queries
- **After**: 2 queries total (1 for exact matches, 1 for partial matches, 1 for all category mappings)

## Performance Improvements

### Expected Performance Gains

1. **Database Query Reduction**: From 1+N queries to 3 queries maximum
2. **Index Usage**: Database can use indexes for fast lookups instead of full table scans
3. **Memory Usage**: Only loads matching columns instead of all columns
4. **Network Round Trips**: Significantly reduced for remote databases

### Typical Performance Improvement

- **Before**: 10+ seconds for remote database
- **After**: Expected 0.5-2 seconds for remote database (5-20x improvement)

## Additional Optimizations

### 1. Caching Strategy

For frequently accessed data, consider implementing caching:

```python
# See caching_strategy.py for implementation
from caching_strategy import column_search_cache

def search_columns_with_cache(columnName: str, db: Session = Depends(get_db)):
    search_term = columnName.strip().lower()
    
    # Check cache first
    cached_results = column_search_cache.get(search_term)
    if cached_results is not None:
        return cached_results
    
    # Perform search and cache results
    results = perform_optimized_search(search_term, db)
    column_search_cache.set(search_term, results)
    return results
```

### 2. Database Connection Pooling

Ensure your database connection pool is properly configured:

```python
# In database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,          # Number of connections to maintain
    max_overflow=30,       # Additional connections beyond pool_size
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600      # Recycle connections after 1 hour
)
```

### 3. Query Timeout Configuration

Add query timeouts to prevent long-running queries:

```python
# Add timeout to database queries
result = db.execute(
    text("SELECT ..."),
    timeout=30  # 30 second timeout
)
```

## Monitoring and Testing

### Performance Testing

Use the provided performance test script:

```bash
python performance_test.py
```

### Database Query Analysis

Enable query logging to monitor performance:

```python
# Add to database.py for development
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

### Key Metrics to Monitor

1. **Response Time**: Should be under 2 seconds for most queries
2. **Database Query Count**: Should be 3 or fewer queries per request
3. **Memory Usage**: Should be minimal (only matching columns loaded)
4. **Database CPU Usage**: Should be low due to index usage

## Troubleshooting

### If Performance is Still Slow

1. **Check Indexes**: Ensure all indexes from `add_performance_indexes.sql` are created
2. **Database Statistics**: Update database statistics: `ANALYZE;`
3. **Query Plan**: Use `EXPLAIN ANALYZE` to check query execution plans
4. **Network Latency**: Consider database connection pooling and keep-alive settings

### Common Issues

1. **Missing Indexes**: Queries will fall back to full table scans
2. **Outdated Statistics**: Database optimizer may choose poor query plans
3. **Network Issues**: High latency between application and database
4. **Resource Constraints**: Insufficient memory or CPU on database server

## Future Optimizations

1. **Read Replicas**: Use read replicas for search queries
2. **Elasticsearch**: Consider full-text search engine for complex searches
3. **Redis Caching**: Implement Redis for distributed caching
4. **CDN**: Cache API responses at the edge for frequently accessed data

