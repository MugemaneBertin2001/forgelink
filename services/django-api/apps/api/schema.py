"""ForgeLink GraphQL Schema."""
import graphene
from graphene_django import DjangoObjectType


class Query(graphene.ObjectType):
    """Root GraphQL Query."""

    hello = graphene.String(default_value="Welcome to ForgeLink Steel Factory IoT")

    # TODO: Add queries for assets, telemetry, alerts


class Mutation(graphene.ObjectType):
    """Root GraphQL Mutation."""

    # TODO: Add mutations for alerts (acknowledge, resolve)
    pass


schema = graphene.Schema(query=Query)
