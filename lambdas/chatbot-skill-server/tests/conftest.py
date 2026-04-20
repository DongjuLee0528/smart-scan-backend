import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_KEY', 'test-service-key')
# magic link JWT (웹 백엔드와 동일한 시크릿 — 테스트용 더미값)
os.environ.setdefault('KAKAO_LINK_JWT_SECRET', 'test-kakao-link-secret-for-unit-tests!!')
os.environ.setdefault('SMARTSCAN_WEB_URL', 'https://smartscan-hub.com')

sys.modules.setdefault('supabase', MagicMock())
sys.modules.setdefault('boto3', MagicMock())
sys.modules.setdefault('resend', MagicMock())
