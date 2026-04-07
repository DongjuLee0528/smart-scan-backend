import os
from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_client() -> Client:
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_SERVICE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)
