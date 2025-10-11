#!/usr/bin/env python3
"""Test script to verify all imports work correctly."""

try:
    import pydantic
    print(f"✅ Pydantic: {pydantic.VERSION}")
except ImportError as e:
    print(f"❌ Pydantic failed: {e}")

try:
    import fastapi
    print(f"✅ FastAPI: {fastapi.__version__}")
except ImportError as e:
    print(f"❌ FastAPI failed: {e}")

try:
    import sqlalchemy
    print(f"✅ SQLAlchemy: {sqlalchemy.__version__}")
except ImportError as e:
    print(f"❌ SQLAlchemy failed: {e}")

try:
    from sqlalchemy.ext import asyncio
    print("✅ SQLAlchemy asyncio extension working")
except ImportError as e:
    print(f"❌ SQLAlchemy asyncio failed: {e}")

print(f"Python executable: {__import__('sys').executable}")
