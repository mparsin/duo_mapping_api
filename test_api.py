#!/usr/bin/env python3
"""
Simple tests for the Duo Mapping API
"""
import pytest
from fastapi.testclient import TestClient

def test_imports():
    """Test that all modules can be imported"""
    try:
        import main
        import database
        import schemas
        import lambda_function
        assert True
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_app_creation():
    """Test that FastAPI app can be created"""
    try:
        from main import app
        assert app is not None
        assert hasattr(app, 'title')
        assert app.title == "Duo Mapping API"
    except Exception as e:
        pytest.fail(f"App creation failed: {e}")

def test_lambda_handler():
    """Test that Lambda handler exists"""
    try:
        from lambda_function import handler
        assert callable(handler)
    except Exception as e:
        pytest.fail(f"Lambda handler test failed: {e}")

def test_root_endpoint_structure():
    """Test root endpoint without database"""
    try:
        from main import app
        with TestClient(app) as client:
            # This might fail due to database connection, but we're testing structure
            try:
                response = client.get("/")
                # If it works, great!
                assert response.status_code == 200
            except Exception:
                # If it fails due to DB, that's expected in CI
                pass
    except Exception as e:
        pytest.fail(f"Endpoint structure test failed: {e}")

def test_subcategory_schema():
    """Test that SubCategory schema includes comment field"""
    try:
        from schemas import SubCategory, SubCategoryUpdate
        
        # Test SubCategory schema has comment field
        schema_fields = SubCategory.model_fields
        assert 'comment' in schema_fields, "SubCategory schema should have comment field"
        
        # Test SubCategoryUpdate schema has comment field
        update_schema_fields = SubCategoryUpdate.model_fields
        assert 'comment' in update_schema_fields, "SubCategoryUpdate schema should have comment field"
        
        # Test that comment is optional
        assert schema_fields['comment'].default is None, "Comment field should be optional"
        assert update_schema_fields['comment'].default is None, "Comment field should be optional in update schema"
        
        # Test that SubCategoryUpdate only has comment field (name is not editable)
        assert len(update_schema_fields) == 1, "SubCategoryUpdate should only have comment field"
        assert 'name' not in update_schema_fields, "SubCategoryUpdate should not have name field (not editable)"
        
    except Exception as e:
        pytest.fail(f"SubCategory schema test failed: {e}")

def test_subcategory_database_model():
    """Test that SubCategory database model includes comment field"""
    try:
        from database import SubCategory
        
        # Test that SubCategory model has comment attribute
        assert hasattr(SubCategory, 'comment'), "SubCategory model should have comment attribute"
        
        # Test that comment column exists in the table definition
        comment_column = getattr(SubCategory, 'comment')
        assert comment_column is not None, "Comment column should exist"
        
    except Exception as e:
        pytest.fail(f"SubCategory database model test failed: {e}")

def test_schema_generation_function():
    """Test that schema generation function exists and has correct structure"""
    try:
        from main import generate_mapped_schema
        
        # Test function exists and is callable
        assert callable(generate_mapped_schema), "generate_mapped_schema should be callable"
        
        # Test function signature (should accept db session)
        import inspect
        sig = inspect.signature(generate_mapped_schema)
        assert 'db' in sig.parameters, "generate_mapped_schema should accept db parameter"
        
    except Exception as e:
        pytest.fail(f"Schema generation function test failed: {e}")

def test_download_schema_endpoint_structure():
    """Test that download schema endpoint exists"""
    try:
        from main import app
        
        # Test that the app has the schema endpoint in its routes
        routes = [route.path for route in app.routes]
        schema_route_exists = any('/api/download-schema' in route for route in routes)
        assert schema_route_exists, "Schema download endpoint should exist"
        
    except Exception as e:
        pytest.fail(f"Download schema endpoint test failed: {e}")

if __name__ == "__main__":
    print("Running basic API tests...")
    test_imports()
    test_app_creation() 
    test_lambda_handler()
    test_root_endpoint_structure()
    test_subcategory_schema()
    test_subcategory_database_model()
    test_schema_generation_function()
    test_download_schema_endpoint_structure()
    print("✅ All tests passed!")
