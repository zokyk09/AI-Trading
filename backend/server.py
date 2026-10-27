"""Compatibility import for older startup commands; prefer backend.main:app."""
from backend.main import app

__all__ = ["app"]
