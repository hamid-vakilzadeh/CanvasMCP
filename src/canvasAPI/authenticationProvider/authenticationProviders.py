from typing import List, Dict, Union, Optional, Literal, Any
from ..base import _get_all_pages, _make_request


def list_authentication_providers(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    all_pages: bool = False,
) -> List[Dict]:
    """
    List authentication providers for an account.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        all_pages: If True, fetch all pages automatically. If False, return only first page.

    Returns:
        List of AuthenticationProvider dictionaries
    """
    if all_pages:
        return _get_all_pages(
            base_url, access_token, "GET", f"/api/v1/accounts/{account_id}/authentication_providers"
        )
    else:
        response = _make_request(
            base_url, access_token, "GET", f"/api/v1/accounts/{account_id}/authentication_providers"
        )
        return response.json()


def get_authentication_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    provider_id: Union[int, str],
) -> Dict:
    """
    Get the specified authentication provider.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        provider_id: Authentication provider ID

    Returns:
        AuthenticationProvider dictionary
    """
    response = _make_request(
        base_url, access_token, "GET", f"/api/v1/accounts/{account_id}/authentication_providers/{provider_id}"
    )
    return response.json()


def create_authentication_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    auth_type: Literal[
        "apple",
        "canvas",
        "cas",
        "clever",
        "facebook",
        "github",
        "google",
        "ldap",
        "linkedin",
        "microsoft",
        "openid_connect",
        "saml",
    ],
    position: Optional[int] = None,
    jit_provisioning: Optional[bool] = None,
    mfa_required: Optional[bool] = None,
    federated_attributes: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict:
    """
    Add external authentication provider for the account.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        auth_type: Authentication provider type
        position: Provider position (1st position is default)
        jit_provisioning: Just In Time provisioning (not valid for Canvas)
        mfa_required: Whether MFA is required when logging in with this provider
        federated_attributes: Federated attributes configuration
        **kwargs: Provider-specific parameters (see API documentation for details)

    Returns:
        Created AuthenticationProvider dictionary

    Raises:
        ValueError: If auth_type is invalid or required parameters are missing
    """
    valid_auth_types = {
        "apple",
        "canvas",
        "cas",
        "clever",
        "facebook",
        "github",
        "google",
        "ldap",
        "linkedin",
        "microsoft",
        "openid_connect",
        "saml",
    }

    if auth_type not in valid_auth_types:
        raise ValueError(
            f"Invalid auth_type '{auth_type}'. "
            f"Allowed values: {', '.join(sorted(valid_auth_types))}"
        )

    data = {"auth_type": auth_type}

    if position is not None:
        data["position"] = position
    if jit_provisioning is not None:
        data["jit_provisioning"] = jit_provisioning
    if mfa_required is not None:
        data["mfa_required"] = mfa_required
    if federated_attributes is not None:
        for key, value in federated_attributes.items():
            data[f"federated_attributes[{key}]"] = value

    # Add provider-specific parameters
    for key, value in kwargs.items():
        data[key] = value

    response = _make_request(
        base_url, access_token, "POST", f"/api/v1/accounts/{account_id}/authentication_providers", data=data
    )
    return response.json()


def update_authentication_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    provider_id: Union[int, str],
    position: Optional[int] = None,
    jit_provisioning: Optional[bool] = None,
    mfa_required: Optional[bool] = None,
    federated_attributes: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Dict:
    """
    Update an authentication provider using the same options as create.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        provider_id: Authentication provider ID
        position: Provider position (1st position is default)
        jit_provisioning: Just In Time provisioning (not valid for Canvas)
        mfa_required: Whether MFA is required when logging in with this provider
        federated_attributes: Federated attributes configuration
        **kwargs: Provider-specific parameters (see API documentation for details)

    Returns:
        Updated AuthenticationProvider dictionary

    Note:
        You cannot update an existing provider to a new authentication type.
    """
    data = {}

    if position is not None:
        data["position"] = position
    if jit_provisioning is not None:
        data["jit_provisioning"] = jit_provisioning
    if mfa_required is not None:
        data["mfa_required"] = mfa_required
    if federated_attributes is not None:
        for key, value in federated_attributes.items():
            data[f"federated_attributes[{key}]"] = value

    # Add provider-specific parameters
    for key, value in kwargs.items():
        data[key] = value

    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/accounts/{account_id}/authentication_providers/{provider_id}",
        data=data,
    )
    return response.json()


def delete_authentication_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    provider_id: Union[int, str],
) -> None:
    """
    Delete the authentication provider configuration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        provider_id: Authentication provider ID

    Returns:
        None
    """
    _make_request(
        base_url,
        access_token,
        "DELETE",
        f"/api/v1/accounts/{account_id}/authentication_providers/{provider_id}",
    )
    return None


def restore_authentication_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    provider_id: Union[int, str],
) -> Dict:
    """
    Restore a deleted authentication provider back to active.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        provider_id: Authentication provider ID

    Returns:
        Restored AuthenticationProvider dictionary

    Note:
        Only available to admins who can manage_account_settings for given root account.
    """
    response = _make_request(
        base_url,
        access_token,
        "PUT",
        f"/api/v1/accounts/{account_id}/authentication_providers/{provider_id}/restore",
    )
    return response.json()


def show_sso_settings(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
) -> Dict:
    """
    Get the current state of each account level setting relevant to Single Sign On configuration.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID

    Returns:
        SSOSettings dictionary
    """
    response = _make_request(base_url, access_token, "GET", f"/api/v1/accounts/{account_id}/sso_settings")
    return response.json()


def update_sso_settings(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    login_handle_name: Optional[str] = None,
    change_password_url: Optional[str] = None,
    auth_discovery_url: Optional[str] = None,
    unknown_user_url: Optional[str] = None,
) -> Dict:
    """
    Update account level SSO settings.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        login_handle_name: The label used for unique login identifiers
        change_password_url: URL to redirect users to for password resets
        auth_discovery_url: Discovery URL for authentication
        unknown_user_url: URL to forward unknown users to

    Returns:
        Updated SSOSettings dictionary

    Note:
        All settings are optional. Any that are not provided are retained as is.
        Null-ish values (blank string, null) will UN-set the setting.
    """
    data = {}

    if login_handle_name is not None:
        data["sso_settings[login_handle_name]"] = login_handle_name
    if change_password_url is not None:
        data["sso_settings[change_password_url]"] = change_password_url
    if auth_discovery_url is not None:
        data["sso_settings[auth_discovery_url]"] = auth_discovery_url
    if unknown_user_url is not None:
        data["sso_settings[unknown_user_url]"] = unknown_user_url

    response = _make_request(
        base_url, access_token, "PUT", f"/api/v1/accounts/{account_id}/sso_settings", data=data
    )
    return response.json()


# Helper methods for creating specific provider types
def create_ldap_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    auth_host: str,
    auth_filter: str,
    auth_username: str,
    auth_password: str,
    auth_port: Optional[int] = None,
    auth_over_tls: Optional[Union[bool, Literal["simple_tls", "start_tls"]]] = None,
    auth_base: Optional[str] = None,
    identifier_format: Optional[str] = None,
    position: Optional[int] = None,
    jit_provisioning: Optional[bool] = None,
    mfa_required: Optional[bool] = None,
) -> Dict:
    """
    Create LDAP authentication provider.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        auth_host: The LDAP server's URL
        auth_filter: LDAP search filter (use {{login}} as placeholder)
        auth_username: Username for LDAP connection
        auth_password: Password for LDAP connection
        auth_port: The LDAP server's TCP port (default: 389)
        auth_over_tls: Whether to use TLS ('simple_tls', 'start_tls', or boolean)
        auth_base: Default treebase parameter for searches
        identifier_format: LDAP attribute to use to look up Canvas login
        position: Provider position
        jit_provisioning: Just In Time provisioning
        mfa_required: Whether MFA is required

    Returns:
        Created AuthenticationProvider dictionary
    """
    return create_authentication_provider(
        base_url=base_url,
        access_token=access_token,
        account_id=account_id,
        auth_type="ldap",
        auth_host=auth_host,
        auth_filter=auth_filter,
        auth_username=auth_username,
        auth_password=auth_password,
        auth_port=auth_port,
        auth_over_tls=auth_over_tls,
        auth_base=auth_base,
        identifier_format=identifier_format,
        position=position,
        jit_provisioning=jit_provisioning,
        mfa_required=mfa_required,
    )


def create_saml_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    idp_entity_id: str,
    log_in_url: str,
    certificate_fingerprint: str,
    identifier_format: str,
    log_out_url: Optional[str] = None,
    requested_authn_context: Optional[str] = None,
    sig_alg: Optional[str] = None,
    metadata: Optional[str] = None,
    metadata_uri: Optional[str] = None,
    position: Optional[int] = None,
    jit_provisioning: Optional[bool] = None,
    mfa_required: Optional[bool] = None,
    federated_attributes: Optional[Dict[str, Any]] = None,
) -> Dict:
    """
    Create SAML authentication provider.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        idp_entity_id: The SAML IdP's entity ID
        log_in_url: The SAML service's SSO target URL
        certificate_fingerprint: The SAML service's certificate fingerprint
        identifier_format: The SAML service's identifier format
        log_out_url: The SAML service's SLO target URL
        requested_authn_context: The SAML AuthnContext
        sig_alg: Signing algorithm for SAML messages
        metadata: XML document to parse as SAML metadata
        metadata_uri: URI to download SAML metadata from
        position: Provider position
        jit_provisioning: Just In Time provisioning
        mfa_required: Whether MFA is required
        federated_attributes: Federated attributes configuration

    Returns:
        Created AuthenticationProvider dictionary
    """
    return create_authentication_provider(
        base_url=base_url,
        access_token=access_token,
        account_id=account_id,
        auth_type="saml",
        idp_entity_id=idp_entity_id,
        log_in_url=log_in_url,
        certificate_fingerprint=certificate_fingerprint,
        identifier_format=identifier_format,
        log_out_url=log_out_url,
        requested_authn_context=requested_authn_context,
        sig_alg=sig_alg,
        metadata=metadata,
        metadata_uri=metadata_uri,
        position=position,
        jit_provisioning=jit_provisioning,
        mfa_required=mfa_required,
        federated_attributes=federated_attributes,
    )


def create_cas_provider(
    base_url: str,
    access_token: str,
    account_id: Union[int, str],
    auth_base: str,
    log_in_url: Optional[str] = None,
    position: Optional[int] = None,
    jit_provisioning: Optional[bool] = None,
    mfa_required: Optional[bool] = None,
) -> Dict:
    """
    Create CAS authentication provider.

    Args:
        base_url: Canvas instance base URL
        access_token: Canvas API access token
        account_id: Account ID
        auth_base: The CAS server's URL
        log_in_url: An alternate SSO URL for logging into CAS
        position: Provider position
        jit_provisioning: Just In Time provisioning
        mfa_required: Whether MFA is required

    Returns:
        Created AuthenticationProvider dictionary
    """
    return create_authentication_provider(
        base_url=base_url,
        access_token=access_token,
        account_id=account_id,
        auth_type="cas",
        auth_base=auth_base,
        log_in_url=log_in_url,
        position=position,
        jit_provisioning=jit_provisioning,
        mfa_required=mfa_required,
    )
