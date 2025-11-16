from typing import Any

def get_remote_address(request: Any) -> str:
    client = getattr(request, 'client', None)
    return getattr(client, 'host', '') if client else ''
