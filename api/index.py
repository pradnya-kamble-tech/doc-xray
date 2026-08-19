"""
Vercel Serverless Function entrypoint for Doc-XRay FastAPI backend.
"""
import os
import sys

# Add project root and apps/api directory to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
api_dir = os.path.join(root_dir, "apps", "api")

for path in [root_dir, api_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from apps.api.main import app
