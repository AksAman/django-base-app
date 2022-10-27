import contextlib
from typing import List
from urllib.parse import urlparse


def _get_ip_address(request):
    import ipaddress

    """Get the remote ip address the request was generated from."""
    ipaddr = request.META.get("HTTP_X_FORWARDED_FOR", None)
    if ipaddr:
        ipaddr = ipaddr.split(",")[0]
    else:
        ipaddr = request.META.get("REMOTE_ADDR", "")

    # Account for IPv4 and IPv6 addresses, each possibly with port appended. Possibilities are:
    # <ipv4 address>
    # <ipv6 address>
    # <ipv4 address>:port
    # [<ipv6 address>]:port
    # Note that ipv6 addresses are colon separated hex numbers
    possibles = (ipaddr.lstrip("[").split("]")[0], ipaddr.split(":")[0])

    for addr in possibles:
        with contextlib.suppress(ValueError):
            return str(ipaddress.ip_address(addr))
    return ipaddr


def _get_user_agent(request):
    """Get the user agent the request was generated from."""
    return request.META.get("HTTP_USER_AGENT", "NA")


def get_request_origin(request):
    """Get the request origin."""
    return request.META.get("HTTP_ORIGIN", None)


def is_request_from_private_origin(request, private_origins: List[str]):
    """
    Default function to determine whether to show the toolbar on a given page.
    """
    if hasattr(request, "user") and request.user and request.user.is_staff:
        return True
    request_origin = get_request_origin(request)
    domain = urlparse(request_origin).netloc
    return domain in private_origins


def is_internal_ip(request, internal_ips, debug=False):
    """
    Default function to determine whether to show the toolbar on a given page.
    """
    if debug:
        print(f"{_get_ip_address(request)} in {internal_ips}")
    if hasattr(request, "user") and request.user and request.user.is_staff:
        return True
    return _get_ip_address(request) in internal_ips
