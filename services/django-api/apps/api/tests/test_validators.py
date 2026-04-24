"""Tests for GraphQL query depth / complexity validators.

These run the validators against parsed GraphQL documents without
touching the schema — they operate at the AST level, which is
exactly where rejection happens in production. The schema-level
integration (validators attached to GraphQLView) is covered by a
separate HTTP test.
"""

from __future__ import annotations

from graphql import parse, validate
from graphql.validation import NoSchemaIntrospectionCustomRule

from apps.api.validators import (
    _count_fields,
    _fragments,
    _measure_depth,
    complexity_limit_validator,
    depth_limit_validator,
)

# ──────────────────────────────────────────────────────────────
# Pure functions — depth measurement
# ──────────────────────────────────────────────────────────────


class TestMeasureDepth:
    def test_flat_query_is_depth_zero(self):
        doc = parse("{ a b c }")
        op = doc.definitions[0]
        assert _measure_depth(op.selection_set, {}) == 0

    def test_one_level_nested(self):
        doc = parse("{ a { b } }")
        op = doc.definitions[0]
        assert _measure_depth(op.selection_set, {}) == 1

    def test_deep_nesting(self):
        doc = parse("{ a { b { c { d { e } } } } }")
        op = doc.definitions[0]
        assert _measure_depth(op.selection_set, {}) == 4

    def test_fragment_spread_followed(self):
        # Hidden depth behind a fragment must be measured, otherwise
        # an attacker bypasses the limit by factoring through fragments.
        doc = parse("""
            { top { ...F } }
            fragment F on Whatever { a { b { c } } }
            """)
        op = doc.definitions[0]
        fragments = _fragments(doc)
        # 'top' → 1 depth increment, fragment adds 2 more (a→b→c) → 3
        assert _measure_depth(op.selection_set, fragments) == 3

    def test_inline_fragment_followed(self):
        doc = parse("{ top { ... on X { a { b } } } }")
        op = doc.definitions[0]
        # top (+1) → inline fragment → a → b (1 extra hop)
        assert _measure_depth(op.selection_set, {}) == 2


# ──────────────────────────────────────────────────────────────
# Pure functions — complexity (field count)
# ──────────────────────────────────────────────────────────────


class TestCountFields:
    def test_single_field(self):
        doc = parse("{ a }")
        op = doc.definitions[0]
        assert _count_fields(op.selection_set, {}) == 1

    def test_siblings(self):
        doc = parse("{ a b c d }")
        op = doc.definitions[0]
        assert _count_fields(op.selection_set, {}) == 4

    def test_nested_counts_all_fields(self):
        doc = parse("{ a { b c { d } } }")
        op = doc.definitions[0]
        # a + b + c + d = 4
        assert _count_fields(op.selection_set, {}) == 4

    def test_fragment_fields_counted(self):
        doc = parse("""
            { ...F }
            fragment F on Query { a b c }
            """)
        op = doc.definitions[0]
        assert _count_fields(op.selection_set, _fragments(doc)) == 3


# ──────────────────────────────────────────────────────────────
# Validator integration — via graphql.validate (no schema needed
# for our rules; they operate on the AST alone)
# ──────────────────────────────────────────────────────────────


def _validate_ast_only(query: str, rules):
    """Run validators without a schema — ok because our rules don't
    need type info, only the AST."""
    from graphql import build_ast_schema

    # Minimal schema so graphql.validate() can construct its context.
    schema = build_ast_schema(parse("type Query { _: String }"))
    document = parse(query)
    # Our rule factories return rule classes; graphql.validate expects
    # a Sequence[Type[ValidationRule]].
    return validate(schema, document, rules)


class TestDepthLimitValidator:
    def test_allows_query_at_limit(self):
        rule = depth_limit_validator(max_depth=3)
        errors = _validate_ast_only("{ a { b { c } } }", [rule])
        # depth=2 (a→b, b→c), limit=3 → allowed.
        assert errors == []

    def test_rejects_query_exceeding_limit(self):
        rule = depth_limit_validator(max_depth=2)
        errors = _validate_ast_only("{ a { b { c { d } } } }", [rule])
        assert len(errors) == 1
        assert "exceeds maximum depth" in errors[0].message
        assert "3 > 2" in errors[0].message

    def test_error_names_the_operation(self):
        rule = depth_limit_validator(max_depth=0)
        errors = _validate_ast_only("query Ops { a { b } }", [rule])
        assert "'Ops'" in errors[0].message

    def test_anonymous_operation_labeled(self):
        rule = depth_limit_validator(max_depth=0)
        errors = _validate_ast_only("{ a { b } }", [rule])
        assert "'<anonymous>'" in errors[0].message


class TestComplexityLimitValidator:
    def test_allows_query_under_limit(self):
        rule = complexity_limit_validator(max_fields=5)
        errors = _validate_ast_only("{ a b c }", [rule])
        assert errors == []

    def test_rejects_query_above_limit(self):
        rule = complexity_limit_validator(max_fields=3)
        # 4 field selections: a, b, c, d
        errors = _validate_ast_only("{ a b c d }", [rule])
        assert len(errors) == 1
        assert "exceeds maximum complexity" in errors[0].message
        assert "4 > 3" in errors[0].message

    def test_nested_fields_counted_together(self):
        rule = complexity_limit_validator(max_fields=3)
        # a + b + c = 3; exactly at the limit → allowed.
        errors = _validate_ast_only("{ a { b { c } } }", [rule])
        assert errors == []

        # One more field pushes it over.
        errors = _validate_ast_only("{ a { b { c d } } }", [rule])
        assert len(errors) == 1


class TestCombinedValidators:
    def test_both_can_fire_on_same_query(self):
        # A deep, wide query trips both rules independently.
        rules = [
            depth_limit_validator(max_depth=2),
            complexity_limit_validator(max_fields=3),
        ]
        errors = _validate_ast_only("{ a { b { c { d e } } } }", rules)
        messages = [e.message for e in errors]
        assert any("maximum depth" in m for m in messages)
        assert any("maximum complexity" in m for m in messages)

    def test_introspection_blocker_rejects_schema_query(self):
        # NoSchemaIntrospectionCustomRule is the off-the-shelf
        # graphql-core rule we slot in when DEBUG=False.
        errors = _validate_ast_only(
            "{ __schema { types { name } } }",
            [NoSchemaIntrospectionCustomRule],
        )
        assert len(errors) >= 1
        assert any("introspection" in e.message.lower() for e in errors)
