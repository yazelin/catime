import httpx
from typing import Optional, Dict, Any


def safe_get_json(
    url: str,
    timeout: float = 10.0,
    max_retries: int = 3,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """Safe HTTP GET returning parsed JSON, with timeout and retries.

    Returns parsed JSON on success, None if response has no JSON.
    Raises httpx exceptions on final failure.
    """
    for attempt in range(max_retries):
        try:
            response = httpx.get(url, timeout=timeout, **kwargs)
            response.raise_for_status()
            try:
                return response.json()
            except Exception:
                return None
        except (httpx.TimeoutException, httpx.HTTPError) as e:
            if attempt == max_retries - 1:
                raise
            continue
    return None
