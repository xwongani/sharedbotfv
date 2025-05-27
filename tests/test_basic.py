import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root_endpoint():
    """Test that the root endpoint returns the expected message"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Inxsource WhatsApp Sales Bot API"}

def test_health_endpoint():
    """Test that the health endpoint returns a healthy status"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ping_endpoint():
    """Test that the ping endpoint returns a pong"""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["message"] == "pong" 