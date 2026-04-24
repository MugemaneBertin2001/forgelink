"""ForgeLink URL Configuration"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from graphene_django.views import GraphQLView
from graphql.validation import NoSchemaIntrospectionCustomRule

from apps.api.validators import complexity_limit_validator, depth_limit_validator
from apps.core.views import health_check, readiness_check

# Build the GraphQL validation pipeline. Depth + complexity always apply;
# introspection is only blocked in prod so GraphiQL still works locally.
_graphql_validators = [
    depth_limit_validator(settings.GRAPHENE_MAX_QUERY_DEPTH),
    complexity_limit_validator(settings.GRAPHENE_MAX_QUERY_COMPLEXITY),
]
if settings.GRAPHQL_DISABLE_INTROSPECTION:
    _graphql_validators.append(NoSchemaIntrospectionCustomRule)

_graphql_view = GraphQLView.as_view(
    graphiql=settings.DEBUG,
    validation_rules=_graphql_validators,
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # Health checks
    path("health/", health_check, name="health-check"),
    path("ready/", readiness_check, name="readiness-check"),
    # OpenAPI schema + browsable docs. The schema endpoint is the
    # contract SDK generators bind against; Swagger and Redoc are
    # for humans exploring the API interactively.
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # GraphQL. graphiql is gated on DEBUG so prod doesn't ship the
    # browsable explorer; introspection is blocked there too.
    path("graphql/", csrf_exempt(_graphql_view)),
    # REST API
    path("api/", include("apps.api.urls")),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]
