# JIRA Story: Develop Duo Mapping API Server

## Epic: ERP Data Mapping Platform

## Story Details

**Story Title:** Develop FastAPI-based Duo Mapping API Server for ERP Data Management

**Story Type:** Feature

**Priority:** High

**Estimate:** 21 Story Points

---

## User Story

**As a** business analyst/data engineer  
**I want** a RESTful API server that manages ERP data mapping relationships  
**So that** I can efficiently map business data fields to ERP table columns and track mapping progress across different categories

---

## Business Context

The Duo Mapping API is a critical component for managing the complex relationships between business data categories and ERP system tables/columns. This server enables users to:

- Organize data into hierarchical categories and sub-categories
- Map business data fields to specific ERP tables and columns
- Track mapping completion progress per category
- Search and discover relevant ERP columns
- Find optimal table matches based on column requirements

---

## Acceptance Criteria

### Core Functionality
- [ ] **Category Management**
  - [ ] Retrieve all categories with mapping progress percentages
  - [ ] Get specific category details by ID
  - [ ] Auto-calculate and update percent_mapped field based on completed mappings

- [ ] **Sub-Category Management**
  - [ ] Retrieve sub-categories filtered by parent category
  - [ ] Support hierarchical organization of data fields

- [ ] **Line Item Management**
  - [ ] Get all lines (data fields) for a specific category
  - [ ] Update line mappings to ERP tables/columns
  - [ ] Support clearing mappings (set to null)
  - [ ] Include table/column names in responses for better UX

- [ ] **ERP Table & Column Management**
  - [ ] Retrieve all available ERP tables
  - [ ] Get columns for specific ERP tables
  - [ ] Validate table/column relationships during updates

- [ ] **Search & Discovery**
  - [ ] Search columns by name with exact and partial matching
  - [ ] Find best table matches based on multiple column names
  - [ ] Return results ranked by relevance

- [ ] **Data Integrity**
  - [ ] Validate foreign key relationships
  - [ ] Auto-recalculate mapping percentages after updates
  - [ ] Provide endpoint to recalculate all category percentages

### API Requirements
- [ ] **RESTful Design**
  - [ ] Use appropriate HTTP methods (GET, PATCH, POST)
  - [ ] Return proper HTTP status codes
  - [ ] Include `/api` prefix for all endpoints

- [ ] **Data Validation**
  - [ ] Validate required fields using Pydantic schemas
  - [ ] Return meaningful error messages
  - [ ] Handle missing resources with 404 responses

- [ ] **CORS Support**
  - [ ] Enable cross-origin requests for web client integration
  - [ ] Configure appropriate headers and methods

### Infrastructure Requirements
- [ ] **Database Integration**
  - [ ] Connect to PostgreSQL database using SQLAlchemy ORM
  - [ ] Support database connection via environment variables
  - [ ] Handle database sessions properly with dependency injection

- [ ] **Containerization**
  - [ ] Dockerized application for consistent deployment
  - [ ] Optimized Docker image with proper caching
  - [ ] Health check endpoint for monitoring

- [ ] **Cloud Deployment**
  - [ ] AWS App Runner configuration
  - [ ] Environment-specific database connections
  - [ ] Deployment automation scripts

### Performance & Quality
- [ ] **Response Performance**
  - [ ] Efficient database queries with proper joins
  - [ ] Pagination consideration for large datasets
  - [ ] Response time under 200ms for standard operations

- [ ] **Code Quality**
  - [ ] Type hints throughout codebase
  - [ ] Proper error handling and logging
  - [ ] Clean separation of concerns (models, schemas, routes)

---

## Technical Requirements

### Technology Stack
- **Framework:** FastAPI 0.116.1+
- **Database:** PostgreSQL with SQLAlchemy 2.0+
- **Validation:** Pydantic schemas
- **Runtime:** Python 3.13
- **Package Manager:** UV
- **Containerization:** Docker
- **Deployment:** AWS App Runner

### Database Schema
```sql
Tables:
- category (id, Name, percent_mapped)
- sub-category (id, name, category_id)
- lines (id, categoryid, default, customer_settings, no_of_chars, field_name, reason, name, sub_category_id, table_id, column_id)
- erp_table (id, name, description)
- erp_column (id, name, comment, type, table_id)
```

### API Endpoints
```
GET /                                    - Health check
GET /api/categories                      - List all categories
GET /api/categories/{id}                 - Get specific category
GET /api/categories/{id}/sub-categories  - Get sub-categories
GET /api/categories/{id}/lines           - Get category lines
GET /api/tables                          - List ERP tables
GET /api/tables/{id}/columns             - Get table columns
PATCH /api/lines/{id}                    - Update line mapping
GET /api/search-columns?columnName=X     - Search columns
POST /api/find-table-matches             - Find matching tables
POST /api/categories/recalculate-percent-mapped - Recalculate percentages
GET /api/health                          - Health check
```

---

## Tasks Breakdown

### Phase 1: Core API Development (8 points)
- [ ] **Task 1.1:** Set up FastAPI application structure with CORS middleware
- [ ] **Task 1.2:** Implement database models using SQLAlchemy (Category, Lines, SubCategory, ERPTable, ERPColumn)
- [ ] **Task 1.3:** Create Pydantic schemas for request/response validation
- [ ] **Task 1.4:** Implement database connection and session management
- [ ] **Task 1.5:** Create basic CRUD endpoints for categories and sub-categories

### Phase 2: Line Management & Mapping (5 points)
- [ ] **Task 2.1:** Implement lines retrieval with table/column name resolution
- [ ] **Task 2.2:** Create line update endpoint with validation
- [ ] **Task 2.3:** Implement percent_mapped calculation logic
- [ ] **Task 2.4:** Add support for clearing mappings (null values)

### Phase 3: ERP Data Management (3 points)
- [ ] **Task 3.1:** Implement ERP tables and columns endpoints
- [ ] **Task 3.2:** Add foreign key validation for table/column relationships
- [ ] **Task 3.3:** Create data seeding utilities for ERP metadata

### Phase 4: Search & Discovery (3 points)
- [ ] **Task 4.1:** Implement column search with exact/partial matching
- [ ] **Task 4.2:** Create table matching algorithm based on column lists
- [ ] **Task 4.3:** Optimize search performance and ranking

### Phase 5: Infrastructure & Deployment (2 points)
- [ ] **Task 5.1:** Create optimized Dockerfile with UV package manager
- [ ] **Task 5.2:** Configure AWS App Runner deployment
- [ ] **Task 5.3:** Set up environment configuration and secrets management
- [ ] **Task 5.4:** Create deployment automation scripts

---

## Definition of Done

- [ ] All acceptance criteria met and tested
- [ ] API endpoints return expected responses with proper status codes
- [ ] Database schema created and populated with sample data
- [ ] Docker image builds successfully and runs without errors
- [ ] Application deploys successfully to AWS App Runner
- [ ] All endpoints tested with sample requests
- [ ] Code follows Python best practices and includes type hints
- [ ] Documentation updated with API endpoint descriptions
- [ ] Health check endpoint responds correctly
- [ ] CORS configuration allows frontend integration

---

## Dependencies

- [ ] PostgreSQL database instance (AWS RDS)
- [ ] AWS App Runner service configuration
- [ ] Environment variables for database connection
- [ ] Sample ERP metadata for testing

---

## Risk Assessment

**High Risk:**
- Database connection failures in production environment
- Performance issues with large datasets during search operations

**Medium Risk:**
- Complex foreign key relationships causing data integrity issues
- CORS configuration blocking frontend requests

**Low Risk:**
- Package dependency conflicts
- Docker build optimization

---

## Notes

- The application uses UV package manager for faster dependency resolution
- Database URL is configurable via environment variables for different environments
- The API includes comprehensive validation and error handling
- Search functionality supports both exact and partial matching for better user experience
- Mapping progress calculation happens automatically after updates to maintain data consistency

---

**Labels:** `api`, `fastapi`, `postgresql`, `aws`, `erp-mapping`, `backend`

**Components:** Duo Mapping API, Database Layer, Search Engine

**Affected Teams:** Backend Development, DevOps, Data Engineering

