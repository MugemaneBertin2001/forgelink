"""GraphQL validation rules — depth and complexity guards.

Graphene does not ship query-size limits; without them a hostile
(or accidentally recursive) client can:

1. Request ``devices { alerts { device { alerts { device { … } } } } }``
   for arbitrary depth, each level exploding the ORM fan-out.
2. Request a flat query with thousands of field selections or page
   past the default page size, forcing the resolver to hydrate
   millions of rows.

The two validators here cap both axes at the validation phase —
before any resolver runs, so the rejection is cheap. Limits are
read from Django settings so an operator can tune them without a
code change.
"""

from __future__ import annotations

from typing import Any

from graphql import GraphQLError
from graphql.language import (
    DocumentNode,
    FieldNode,
    FragmentDefinitionNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    OperationDefinitionNode,
    SelectionSetNode,
)
from graphql.validation import ValidationContext, ValidationRule


def _fragments(document: DocumentNode) -> dict[str, FragmentDefinitionNode]:
    return {
        defn.name.value: defn
        for defn in document.definitions
        if isinstance(defn, FragmentDefinitionNode)
    }


def _measure_depth(
    selection_set: SelectionSetNode | None,
    fragments: dict[str, FragmentDefinitionNode],
) -> int:
    """Return the maximum nesting depth of a selection set.

    Inline fragments and fragment spreads are followed so a
    query that hides its depth behind a fragment is still
    counted correctly.
    """
    if selection_set is None:
        return 0

    max_depth = 0
    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            child_depth = _measure_depth(selection.selection_set, fragments)
            # +1 for the field itself when it has a child selection set;
            # leaf fields count as depth 0 to keep limits intuitive
            # ("how many hops of nesting").
            depth = child_depth + (1 if selection.selection_set else 0)
            max_depth = max(max_depth, depth)
        elif isinstance(selection, InlineFragmentNode):
            max_depth = max(
                max_depth, _measure_depth(selection.selection_set, fragments)
            )
        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment is not None:
                max_depth = max(
                    max_depth, _measure_depth(fragment.selection_set, fragments)
                )
    return max_depth


def _count_fields(
    selection_set: SelectionSetNode | None,
    fragments: dict[str, FragmentDefinitionNode],
) -> int:
    """Count every field selection, following fragments.

    Used as a crude complexity proxy — a query with 2,000 fields
    is almost certainly either a mistake or an abuse attempt.
    """
    if selection_set is None:
        return 0

    total = 0
    for selection in selection_set.selections:
        if isinstance(selection, FieldNode):
            total += 1
            total += _count_fields(selection.selection_set, fragments)
        elif isinstance(selection, InlineFragmentNode):
            total += _count_fields(selection.selection_set, fragments)
        elif isinstance(selection, FragmentSpreadNode):
            fragment = fragments.get(selection.name.value)
            if fragment is not None:
                total += _count_fields(fragment.selection_set, fragments)
    return total


def depth_limit_validator(max_depth: int):
    """Factory: returns a ValidationRule class that caps depth."""

    class _DepthLimit(ValidationRule):
        def __init__(self, context: ValidationContext) -> None:
            super().__init__(context)
            self._fragments = _fragments(context.document)

        def enter_operation_definition(
            self, node: OperationDefinitionNode, *_: Any
        ) -> None:
            depth = _measure_depth(node.selection_set, self._fragments)
            if depth > max_depth:
                op_name = node.name.value if node.name else "<anonymous>"
                self.report_error(
                    GraphQLError(
                        f"Query '{op_name}' exceeds maximum depth "
                        f"({depth} > {max_depth}). Break the query into "
                        "smaller pieces or raise GRAPHENE_MAX_QUERY_DEPTH."
                    )
                )

    _DepthLimit.__name__ = f"DepthLimit{max_depth}Rule"
    return _DepthLimit


def complexity_limit_validator(max_fields: int):
    """Factory: returns a ValidationRule class that caps field count."""

    class _ComplexityLimit(ValidationRule):
        def __init__(self, context: ValidationContext) -> None:
            super().__init__(context)
            self._fragments = _fragments(context.document)

        def enter_operation_definition(
            self, node: OperationDefinitionNode, *_: Any
        ) -> None:
            count = _count_fields(node.selection_set, self._fragments)
            if count > max_fields:
                op_name = node.name.value if node.name else "<anonymous>"
                self.report_error(
                    GraphQLError(
                        f"Query '{op_name}' exceeds maximum complexity "
                        f"({count} > {max_fields} field selections). "
                        "Paginate or request fewer fields."
                    )
                )

    _ComplexityLimit.__name__ = f"ComplexityLimit{max_fields}Rule"
    return _ComplexityLimit
