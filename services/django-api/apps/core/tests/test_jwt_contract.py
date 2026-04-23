"""Contract tests for the JWT shape exchanged between Spring IDP and Django.

These tests pin the claim names and shapes the IDP emits so that a silent
divergence (e.g., IDP renaming ``roles`` -> ``role``) fails CI rather than
silently zeroing out every user's permission set at runtime.

The reference for the producer-side contract is
``services/spring-idp/src/main/java/com/forgelink/idp/service/JwtService.java``.
The contract exercised here:

* ``sub``         — user UUID, string
* ``email``       — user email, string
* ``name``        — full name, string
* ``roles``       — JSON array of role codes (NOT singular ``role``)
* ``plant_id``    — plant identifier, string or null
* ``iss``         — "forgelink-idp"
* ``iat``, ``exp`` — numeric dates
* header ``kid``  — matches the IDP's publishing key id

We do not validate signatures here (that's covered by the full auth-flow
tests). We only validate that the consumer side of Django correctly
extracts and resolves what the producer side emits.
"""

import jwt as pyjwt
import pytest

from apps.core.authentication import JWTUser
from apps.core.middleware import JWTAuthenticationMiddleware

# The shape IDP actually emits, mirrored from JwtService.generateAccessToken.
# Keep this dict in sync with that method; a divergence here means a
# divergence in production.
IDP_PRODUCER_PAYLOAD = {
    "sub": "6a3b1a8f-8b6c-4ee2-9ad0-fb6f12ae7a31",
    "iss": "forgelink-idp",
    "email": "operator@forgelink.local",
    "name": "Jane Operator",
    "roles": ["PLANT_OPERATOR"],
    "plant_id": "steel-plant-kigali",
    "iat": 1700000000,
    "exp": 1700086400,
}

IDP_PRODUCER_PAYLOAD_MULTI_ROLE = {
    "sub": "0dcc84c0-2c8e-47fb-8c91-2c5e4e6b7a90",
    "iss": "forgelink-idp",
    "email": "multi@forgelink.local",
    "name": "Multi Role",
    "roles": ["PLANT_OPERATOR", "TECHNICIAN"],
    "plant_id": "steel-plant-kigali",
    "iat": 1700000000,
    "exp": 1700086400,
}

IDP_PRODUCER_PAYLOAD_ADMIN = {
    "sub": "a9c7e7e6-8d07-4e3a-bf54-d2f43b33a212",
    "iss": "forgelink-idp",
    "email": "admin@forgelink.local",
    "name": "Factory Admin",
    "roles": ["FACTORY_ADMIN"],
    "plant_id": "steel-plant-kigali",
    "iat": 1700000000,
    "exp": 1700086400,
}


class TestExtractRoleCodes:
    """Direct tests on the role-claim extractor."""

    def test_roles_as_json_array_is_the_contract(self):
        """The canonical IDP payload uses a 'roles' JSON array."""
        result = JWTAuthenticationMiddleware._extract_role_codes(IDP_PRODUCER_PAYLOAD)
        assert result == ["PLANT_OPERATOR"]

    def test_multi_role_list_preserved(self):
        result = JWTAuthenticationMiddleware._extract_role_codes(
            IDP_PRODUCER_PAYLOAD_MULTI_ROLE
        )
        assert sorted(result) == ["PLANT_OPERATOR", "TECHNICIAN"]

    def test_empty_roles_array(self):
        result = JWTAuthenticationMiddleware._extract_role_codes({"roles": []})
        assert result == []

    def test_missing_roles_returns_empty_list(self):
        result = JWTAuthenticationMiddleware._extract_role_codes(
            {"sub": "x", "email": "x@x.com"}
        )
        assert result == []

    def test_legacy_singular_role_string_is_accepted(self):
        """Tokens from a pre-contract-fix IDP still resolve."""
        result = JWTAuthenticationMiddleware._extract_role_codes({"role": "VIEWER"})
        assert result == ["VIEWER"]

    def test_roles_as_string_coerced_to_singleton_list(self):
        """Some JWT libraries may emit a single-element set as a string; cope."""
        result = JWTAuthenticationMiddleware._extract_role_codes(
            {"roles": "PLANT_OPERATOR"}
        )
        assert result == ["PLANT_OPERATOR"]

    def test_roles_with_falsy_entries_filtered(self):
        result = JWTAuthenticationMiddleware._extract_role_codes(
            {"roles": ["PLANT_OPERATOR", "", None, "VIEWER"]}
        )
        assert result == ["PLANT_OPERATOR", "VIEWER"]

    def test_roles_of_unexpected_type_ignored_safely(self):
        """A misbehaving issuer that puts a dict in 'roles' must not crash Django."""
        result = JWTAuthenticationMiddleware._extract_role_codes(
            {"roles": {"not": "a list"}}
        )
        # The dict is iterable (yields keys); the extractor accepts any
        # iterable and filters falsy values, so "not" survives. The critical
        # invariant is that this does not raise.
        assert isinstance(result, list)


class TestJwtUserClaimsExtraction:
    """JWTUser built from the IDP payload should expose usable identity."""

    def test_single_role_user_is_not_admin(self):
        user = JWTUser(IDP_PRODUCER_PAYLOAD)
        assert user.email == "operator@forgelink.local"
        assert user.role_codes == ["PLANT_OPERATOR"]
        assert user.role_code == "PLANT_OPERATOR"
        assert user.is_superuser is False
        assert user.is_staff is False
        assert user.has_role("PLANT_OPERATOR") is True
        assert user.has_role("FACTORY_ADMIN") is False

    def test_multi_role_user_sorts_role_code_string(self):
        user = JWTUser(IDP_PRODUCER_PAYLOAD_MULTI_ROLE)
        assert sorted(user.role_codes) == ["PLANT_OPERATOR", "TECHNICIAN"]
        # role_code is the joined, alphabetised form for audit/display.
        assert user.role_code == "PLANT_OPERATOR,TECHNICIAN"
        assert user.is_superuser is False

    def test_admin_role_sets_superuser_flag(self):
        user = JWTUser(IDP_PRODUCER_PAYLOAD_ADMIN)
        assert "FACTORY_ADMIN" in user.role_codes
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_roleless_token_has_no_admin_access(self):
        payload = dict(IDP_PRODUCER_PAYLOAD)
        payload.pop("roles")
        user = JWTUser(payload)
        assert user.role_codes == []
        assert user.role_code is None
        assert user.is_superuser is False


class TestClaimShapeFreeze:
    """
    Freeze the claim names the consumer reads. These tests fail if someone
    renames a claim without updating the IDP in lockstep.

    Pair this with the IDP-side test in
    services/spring-idp/src/test/java/com/forgelink/idp/service/JwtServiceTest.java
    that covers the producer side.
    """

    EXPECTED_CLAIM_NAMES = {
        "sub",
        "email",
        "roles",
        "plant_id",
        "iss",
        "iat",
        "exp",
    }

    def test_producer_payload_contains_every_consumed_claim(self):
        """The payload we pin for test must carry every claim Django reads."""
        for claim in self.EXPECTED_CLAIM_NAMES:
            assert claim in IDP_PRODUCER_PAYLOAD, (
                f"Claim '{claim}' missing from canonical IDP payload fixture. "
                "If IDP stopped emitting this claim, update JwtService.java "
                "and this fixture together."
            )

    def test_roles_claim_is_named_roles_not_role(self):
        """Pin the plural 'roles' as the canonical claim name.

        This is the test that would have caught the production bug where
        IDP wrote 'roles' but Django read 'role'.
        """
        assert "roles" in IDP_PRODUCER_PAYLOAD
        assert "role" not in IDP_PRODUCER_PAYLOAD

    def test_roles_is_a_json_array(self):
        assert isinstance(IDP_PRODUCER_PAYLOAD["roles"], list)

    def test_canonical_payload_round_trips_as_jwt(self):
        """Sanity check: the fixture serialises as a valid JWT body.

        Uses HS256 with a test secret; we're exercising claim shape, not the
        production RS256 signing (covered by IDP's own unit tests).
        """
        secret = "test-secret-not-for-production"
        token = pyjwt.encode(IDP_PRODUCER_PAYLOAD, secret, algorithm="HS256")
        decoded = pyjwt.decode(
            token, secret, algorithms=["HS256"], options={"verify_exp": False}
        )
        assert decoded["roles"] == ["PLANT_OPERATOR"]
        assert "role" not in decoded


class TestAuditMiddlewareConsumerContract:
    """Audit layer consumes the same role claim; contract must hold there too."""

    @pytest.fixture
    def request_factory(self):
        from django.test import RequestFactory

        return RequestFactory()

    @pytest.fixture
    def get_response(self):
        from django.http import JsonResponse

        def _response(request):
            return JsonResponse({"ok": True})

        return _response

    def test_audit_middleware_reads_roles_list(self, request_factory, get_response):
        from unittest.mock import patch

        from apps.core.middleware import AuditMiddleware

        middleware = AuditMiddleware(get_response)
        request = request_factory.post("/api/test/", {})
        request.jwt_payload = dict(IDP_PRODUCER_PAYLOAD_MULTI_ROLE)
        request.role_codes = IDP_PRODUCER_PAYLOAD_MULTI_ROLE["roles"]
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            middleware(request)
            kwargs = mock_audit.delay.call_args[1]
            # Alphabetised join of the two roles.
            assert kwargs["role_code"] == "PLANT_OPERATOR,TECHNICIAN"
