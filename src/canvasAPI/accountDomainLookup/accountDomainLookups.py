from typing import Dict, List, Optional
from ..base import _make_request


def search_account_domains(
    base_url: str,
    access_token: str,
    name: Optional[str] = None,
    domain: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> List[Dict]:
    """
    Search for account domains.

    Returns a list of up to 5 matching account domains.
    Partial match on name / domain are supported.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        name: Campus name
        domain: Domain name
        latitude: Latitude coordinate
        longitude: Longitude coordinate

    Returns:
        List of matching account domains with the following structure:
        [
            {
                "name": "University Name",
                "domain": "domain.edu",
                "distance": null,
                "authentication_provider": "canvas"
            },
            ...
        ]
    """
    params = {}

    if name is not None:
        params["name"] = name
    if domain is not None:
        params["domain"] = domain
    if latitude is not None:
        params["latitude"] = latitude
    if longitude is not None:
        params["longitude"] = longitude

    response = _make_request(base_url, access_token, "GET", "/api/v1/accounts/search", params=params)
    return response.json()
