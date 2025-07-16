from typing import Dict, List, Optional
from ..base import CanvasAPIBase


class AccountDomainLookups(CanvasAPIBase):
    """Canvas API client for account domain lookups."""

    def search(
        self,
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

        response = self._make_request("GET", "/api/v1/accounts/search", params=params)
        return response.json()


account_domain_lookups = AccountDomainLookups()
