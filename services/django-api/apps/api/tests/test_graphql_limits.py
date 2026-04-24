"""End-to-end tests for GraphQL query limits at the HTTP boundary.

These tests post queries at ``/graphql/`` and assert that the
validation rules attached to GraphQLView in apps.core.urls reject
oversized queries. Without these, the validator unit tests could
stay green while a config drift silently unwires them from the view.

GraphQLView captures validation_rules at ``as_view()`` time (module
import), so ``override_settings`` won't rebuild the view. These
tests therefore hit the **actual** configured limits (depth=10,
complexity=1000) rather than overriding them.
"""

from __future__ import annotations

import json

from django.test import Client

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def graphql_client():
    return Client()


def _post(client: Client, query: str):
    response = client.post(
        "/graphql/",
        data=json.dumps({"query": query}),
        content_type="application/json",
    )
    return response


def _deep_query(depth: int) -> str:
    """Generate a query that nests ``depth`` selection sets deep.

    The query isn't schema-valid but that doesn't matter — our
    depth validator runs before schema validation and rejects on
    AST shape alone.
    """
    body = "x"
    for _ in range(depth):
        body = f"a {{ {body} }}"
    return "{ " + body + " }"


class TestDepthLimitAtHttpBoundary:
    def test_deeply_nested_query_rejected(self, graphql_client):
        # 15 levels well over the default of 10.
        response = _post(graphql_client, _deep_query(15))
        body = response.json()
        assert "errors" in body
        assert any("exceeds maximum depth" in err["message"] for err in body["errors"])

    def test_shallow_query_passes_depth_check(self, graphql_client):
        # 2 levels is well under 10 — any errors in the response must
        # be about the schema (unknown field), NOT about depth.
        response = _post(graphql_client, _deep_query(2))
        body = response.json()
        messages = [e.get("message", "") for e in body.get("errors", [])]
        assert not any("exceeds maximum depth" in m for m in messages)


class TestIntrospectionGateByDebugFlag:
    def test_typename_query_works_in_debug(self, graphql_client):
        # DEBUG=True in CI & local. GraphiQL needs __typename /
        # __schema to render its docs panel — make sure we didn't
        # over-block locally.
        response = _post(graphql_client, "{ __typename }")
        body = response.json()
        messages = [e.get("message", "") for e in body.get("errors", [])]
        assert not any(
            "introspection" in m.lower() and "disabled" in m.lower() for m in messages
        )
