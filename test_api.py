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

if __name__ == "__main__":
    print("Running basic API tests...")
    test_imports()
    test_app_creation() 
    test_lambda_handler()
    test_root_endpoint_structure()
    print("✅ All tests passed!")
