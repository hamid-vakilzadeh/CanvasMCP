"""Authentication Provider-related Canvas API modules

Provides APIs for managing authentication providers and SSO settings.
"""

from .authenticationProviders import AuthenticationProvidersAPI, authentication_providers

__all__ = [
    "AuthenticationProvidersAPI",
    "authentication_providers",
]