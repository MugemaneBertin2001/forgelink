"""drf-spectacular extensions for ForgeLink-specific DRF classes.

These register OpenAPI schema hints for our custom authentication
class so the generated spec documents the Bearer-token scheme that
Flutter / SDK clients will actually use.
"""

from drf_spectacular.authentication import OpenApiAuthenticationExtension


class JWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """OpenAPI schema for apps.core.authentication.JWTAuthentication."""

    target_class = "apps.core.authentication.JWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "RS256-signed JWT issued by the ForgeLink Spring IDP. "
                "Public keys are fetched from the IDP's JWKS endpoint "
                "and cached for one hour."
            ),
        }
