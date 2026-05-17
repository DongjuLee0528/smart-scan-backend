"""
Database client wrapper for outbound-notifier Lambda function

Provides Supabase database connection by importing from shared Lambda module.
Used for retrieving user and family data for email notification sending.
"""

from lambda_shared.database import get_client
