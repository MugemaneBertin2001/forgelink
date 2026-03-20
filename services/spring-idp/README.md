# ForgeLink Identity Provider (IDP)

Zero-trust identity provider for the ForgeLink steel factory IoT platform.

## Overview

The IDP is a headless Spring Boot service that handles:

- User authentication (username/password → JWT)
- JWT token issuance (RS256)
- JWKS endpoint for other services
- Token refresh and revocation
- RBAC role management

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Authenticate and receive JWT + refresh token |
| POST | `/auth/refresh` | Exchange refresh token for new JWT |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/jwks` | Public key for JWT verification (JWKS format) |
| GET | `/auth/validate` | Token introspection |

## Token Specification

- **Algorithm**: RS256
- **Access Token**: 24 hour expiry
- **Refresh Token**: 30 day expiry, stored in Redis
- **Claims**: `sub`, `roles`, `plant_id`, `iat`, `exp`

## RBAC Roles

| Role | Description |
|------|-------------|
| `FACTORY_ADMIN` | Full access - users, config, all data |
| `PLANT_OPERATOR` | Read all, write alerts/commands |
| `TECHNICIAN` | Read own area, acknowledge alerts |
| `VIEWER` | Read-only access |

## Environment Variables

```bash
# Database
IDP_DB_HOST=postgres
IDP_DB_PORT=5432
IDP_DB_NAME=idp
IDP_DB_USER=idp
IDP_DB_PASSWORD=

# Redis (for token blacklist)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_IDP_DB=1

# JWT Keys
IDP_JWT_PRIVATE_KEY_PATH=/app/secrets/jwt-private.pem
IDP_JWT_PUBLIC_KEY_PATH=/app/secrets/jwt-public.pem
IDP_JWT_EXPIRY_HOURS=24
IDP_REFRESH_EXPIRY_DAYS=30
IDP_JWT_ISSUER=forgelink-idp
```

## Local Development

```bash
# From services/spring-idp
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# Or with Docker
docker compose up forgelink-idp
```

## Running Tests

```bash
mvn test
```

## API Documentation

- OpenAPI: http://localhost:8080/api-docs
- Swagger UI: http://localhost:8080/swagger-ui.html

## Security Notes

- Private key never leaves this service
- All other services fetch public key via JWKS endpoint
- Refresh tokens are stored in Redis for fast revocation
- Passwords are hashed with BCrypt
