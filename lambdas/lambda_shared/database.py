"""
Supabase Database Client Management

Utility for managing Supabase database connections for RFID scan data processing.
Supports connection pooling and caching for efficient database access in Lambda functions.

Key Features:
- Supabase client singleton management
- Secure credential management through environment variables
- Performance optimization through LRU cache connection reuse

Security Settings:
- SUPABASE_SERVICE_KEY: Uses backend-dedicated service key
- Sensitive information protection through environment variables
- Secure DB access in Lambda execution environment

Usage Context:
- Real-time storage of RFID scan data
- Logging of item status change records
- User device information lookup
- Scan event notification processing

Performance Optimization:
- Single client instance reuse
- Lambda Cold Start time reduction
- Response time improvement through connection pooling
"""

import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    """
    Returns Supabase client singleton instance

    Uses LRU cache to reuse client instances for efficient
    database access in Lambda functions.

    Returns:
        Client: Supabase client instance

    Raises:
        ValueError: When required environment variables are not set

    Environment Variables:
        SUPABASE_URL: Supabase project URL
        SUPABASE_SERVICE_KEY: Backend-dedicated service key

    Usage Example:
        Called when storing RFID scan data to database
    """
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)