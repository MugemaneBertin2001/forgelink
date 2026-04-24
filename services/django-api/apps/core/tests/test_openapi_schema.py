"""Tests that pin the OpenAPI contract.

The committed ``docs/api/openapi.yml`` is the source of truth that
Flutter / any future SDK generator binds against. These tests fail
loudly if:

1. Schema generation raises (something regressed at the view layer,
   e.g. a permission class stopped being callable).
2. The committed spec and the code have drifted — the generator
   produces something different from what's checked in.

A green CI thus means the spec file on disk matches the code.
"""

from __future__ import annotations

import io
from pathlib import Path

from django.core.management import call_command

import pytest
import yaml

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.yml"


def _generate() -> str:
    """Invoke ``manage.py spectacular`` and return the rendered YAML."""
    buf = io.StringIO()
    call_command("spectacular", stdout=buf)
    return buf.getvalue()


class TestOpenAPISchema:
    def test_schema_generates_without_raising(self):
        # Must not raise. A failure here means at least one view has
        # a bug that stops spectacular from walking the URL tree —
        # most commonly a permission_classes entry that isn't
        # callable (see the HasPermission __call__ regression pinned
        # by test_permissions).
        yaml_text = _generate()
        assert yaml_text, "schema output was empty"

    def test_schema_is_valid_yaml(self):
        doc = yaml.safe_load(_generate())
        assert doc["openapi"].startswith("3."), f"unexpected version: {doc['openapi']}"
        assert doc["info"]["title"] == "ForgeLink API"

    def test_bearer_auth_scheme_registered(self):
        # The JWTAuthentication extension in apps.core.schema should
        # put a BearerAuth security scheme into components. Without it
        # the SDK generator produces endpoints with no auth baked in.
        doc = yaml.safe_load(_generate())
        schemes = doc.get("components", {}).get("securitySchemes", {})
        assert "BearerAuth" in schemes
        assert schemes["BearerAuth"]["type"] == "http"
        assert schemes["BearerAuth"]["scheme"] == "bearer"

    def test_committed_schema_matches_generated(self):
        # Drift guard: if this test fails, someone changed a view
        # without re-running ``make openapi`` (or the CI equivalent).
        # Regenerate with:
        #     python manage.py spectacular \
        #         --file docs/api/openapi.yml
        # and commit the result.
        if not SCHEMA_PATH.exists():
            pytest.fail(
                f"{SCHEMA_PATH} does not exist. Run "
                "`python manage.py spectacular --file docs/api/openapi.yml`."
            )
        committed = SCHEMA_PATH.read_text()
        generated = _generate()
        assert committed == generated, (
            "docs/api/openapi.yml is out of date with the code. "
            "Regenerate with `python manage.py spectacular "
            "--file docs/api/openapi.yml` and commit the result."
        )
