"""Vercel ASGI entry point for GovMate AI.

Vercel auto-detects this file as an ASGI app. It imports the FastAPI
application from the backend package and uses it as the serverless handler.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
