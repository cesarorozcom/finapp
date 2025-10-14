#!/usr/bin/env python3
"""
Script to run FastAPI server alongside Django
"""
import uvicorn
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'budget_tracker.settings')
django.setup()

if __name__ == "__main__":
    uvicorn.run(
        "fastapi_app:app",
        host="127.0.0.1",
        port=8001,  # Different port from Django (8000)
        reload=True,
        log_level="info"
    )