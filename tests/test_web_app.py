"""Tests for the FastAPI web application."""

from fastapi.testclient import TestClient

from src.web_app import app


def test_favicon_is_served():
    response = TestClient(app).get("/favicon.ico")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "<svg" in response.text
