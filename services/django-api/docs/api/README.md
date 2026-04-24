# ForgeLink REST API — OpenAPI

The `openapi.yml` file at this path is the **contract** that any
client SDK (starting with the Flutter app) generates against. It is
checked into git and CI asserts it stays in sync with the Django
code via `test_openapi_schema::test_committed_schema_matches_generated`.

## Browsing the API

| Route | What |
| --- | --- |
| `/api/schema/` | Raw OpenAPI 3.0 YAML — what SDK generators consume |
| `/api/docs/` | Swagger UI — interactive, supports "Try it out" with a Bearer token |
| `/api/redoc/` | Redoc — read-only browsable docs |
| `/graphql/` | GraphiQL — the GraphQL surface is **not** in this spec (see below) |

To authenticate in Swagger: log in via the Spring IDP
(`POST http://localhost:8080/auth/login`), copy the `access_token`
from the response, click **Authorize** in Swagger, paste the token.

## Regenerating the spec

After any view / serializer change:

```bash
python manage.py spectacular --file docs/api/openapi.yml
```

Commit the result. CI fails if you skip this.

## What's in the spec vs. what's not

**In**: every DRF `ModelViewSet`, `GenericAPIView`, and serializer in
`apps/assets`, `apps/alerts`, `apps/telemetry`, `apps/simulator`,
`apps/audit`. Bearer auth is documented via the JWTAuthentication
extension in `apps/core/schema.py`.

The nine `APIView` / `ViewSet` endpoints that previously fell
back to an empty response shape now carry explicit
`@extend_schema` annotations:

- `AlertStatsView` — typed via `AlertStatsSerializer`
- `AreaViewSet` (telemetry) — `OpenApiTypes.OBJECT` per action
- `AssetDashboardView` — `OpenApiTypes.OBJECT`
- `PlantDashboardView` — `OpenApiTypes.OBJECT`
- `SimulatorDashboardViewSet` — `OpenApiTypes.OBJECT`
- `TDengineSchemaView` — inline `{message: str}`
- `TelemetryEventView` — `TelemetryEventSerializer` in, `{message}` out
- `TelemetryViewSet` — `OpenApiTypes.OBJECT` per action
- `slack_webhook` — inline `{ok?: bool, challenge?: str}`

The dashboard-style endpoints that roll up ad-hoc fields are
documented as generic objects on purpose — the UI iterates fast
on those shapes, and a fake-precise SDK binding would be worse
than a loose one. Endpoints with stable shapes bind to real
serializers.

Spectacular still emits two cosmetic `unable to guess serializer`
warnings for `TelemetryViewSet` and `SimulatorDashboardViewSet`
because both are bare `ViewSet`s with only `@action` methods (no
standard `list` / `retrieve`). Each action still generates
correct spec output; the warning refers to the router's synthetic
collection endpoint that doesn't actually exist.

**Not in scope for OpenAPI**: the GraphQL surface. GraphQL has its
own self-describing schema exposed at `/graphql/` with GraphiQL; an
SDK that needs it uses a GraphQL-specific codegen (e.g. `genql`),
not OpenAPI.

## GraphQL

Queries exposed by `apps.api.schema`:

- `deviceHistory` — historical telemetry
- `deviceLatest` — latest device value
- `deviceStatistics` — aggregate stats
- `deviceAnomalies` — anomaly detection
- `latestValues` — latest for many devices
- `compareDevices` — multi-device comparison
- `areaOverview` — per-area rollup
- `plantDashboard` — plant-wide summary

Mutations go through the same JWT middleware as REST — the
`_require_permission` helper in `apps/api/schema.py` enforces the
same permission codes as the REST permission classes.
