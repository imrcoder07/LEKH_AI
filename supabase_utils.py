import os


def get_supabase_client():
    """Create a Supabase client from environment settings.

    Raises:
        RuntimeError: if required environment variables are missing.
    """
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured in the environment.")

    return create_client(url, key)
