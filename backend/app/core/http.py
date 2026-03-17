"""
Proxy-safe HTTP client factories.

The system has ALL_PROXY=socks5h://... which httpx cannot handle.
These helpers create httpx clients that bypass environment proxy settings.
"""
import httpx


def make_httpx_client(timeout: float = 60.0, **kwargs) -> httpx.Client:
    """Create a sync httpx.Client that ignores environment proxy vars."""
    transport = httpx.HTTPTransport()
    return httpx.Client(transport=transport, timeout=timeout, **kwargs)


def make_async_httpx_client(timeout: float = 60.0, **kwargs) -> httpx.AsyncClient:
    """Create an async httpx.AsyncClient that ignores environment proxy vars."""
    transport = httpx.AsyncHTTPTransport()
    return httpx.AsyncClient(transport=transport, timeout=timeout, **kwargs)
