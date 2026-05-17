"""
Database client wrapper for inbound-scanner Lambda function

Provides Supabase database connection by importing from shared Lambda module.
Used for device lookup, item management, and scan log recording operations.
"""

from lambda_shared.database import get_client
