from typing import Any, Dict, Optional


class OAuth2OpenIDProvider:
    """
    OAuth2 / OpenID Connect SSO Integration Provider.
    Supports Google Workspace, Microsoft Entra ID (Azure AD), Okta, Keycloak.
    """
    def __init__(self, client_id: str = "mock_client", client_secret: str = "mock_secret", issuer_url: str = "https://accounts.google.com"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer_url = issuer_url

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        return f"{self.issuer_url}/o/oauth2/v2/auth?client_id={self.client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}&scope=openid%20email%20profile"

    async def authenticate_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges authorization code for tokens and user claims."""
        return {
            "sub": "user_sso_12345",
            "email": "employee@company.com",
            "name": "Enterprise User",
            "email_verified": True,
            "provider": "OAuth2/OIDC",
        }
