"""
Test configuration for remote-alert Lambda function

Sets up test environment with mock external dependencies and environment variables.
Mocks Supabase client, boto3, and Resend email service for isolated unit testing.
"""

import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault('RESEND_API_KEY', 'test-key')
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'test-service-key')

sys.modules.setdefault('supabase', MagicMock())
sys.modules.setdefault('boto3', MagicMock())
sys.modules.setdefault('resend', MagicMock())
