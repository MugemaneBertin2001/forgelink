"""ForgeLink URL Configuration"""

from django.contrib import admin
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from graphene_django.views import GraphQLView

from apps.core.views import health_check, readiness_check

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
    # GraphQL
    path("graphql/", csrf_exempt(GraphQLView.as_view(graphiql=True))),
    # REST API
    path("api/", include("apps.api.urls")),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]
