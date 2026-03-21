"""ForgeLink GraphQL Schema."""
import graphene
from graphene_django import DjangoObjectType

from apps.telemetry.schema import TelemetryQuery


class Query(TelemetryQuery, graphene.ObjectType):
    """Root GraphQL Query.

    Inherits from:
    - TelemetryQuery: Device history, statistics, anomalies, dashboard
    """

    hello = graphene.String(default_value="Welcome to ForgeLink Steel Factory IoT")
    version = graphene.String(default_value="1.0.0")

    # TODO: Add queries for assets, alerts


class Mutation(graphene.ObjectType):
    """Root GraphQL Mutation."""

    # TODO: Add mutations for alerts (acknowledge, resolve)
    pass


schema = graphene.Schema(query=Query)
