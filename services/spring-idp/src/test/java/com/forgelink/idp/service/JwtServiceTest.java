package com.forgelink.idp.service;

import com.forgelink.idp.config.JwtConfig;
import com.forgelink.idp.model.Role;
import com.forgelink.idp.model.User;
import com.forgelink.idp.repository.RefreshTokenRepository;
import io.jsonwebtoken.Claims;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

@ExtendWith(MockitoExtension.class)
class JwtServiceTest {

    @Mock
    private RefreshTokenRepository refreshTokenRepository;

    private JwtConfig jwtConfig;
    private KeyService keyService;
    private JwtService jwtService;

    @BeforeEach
    void setUp() {
        jwtConfig = new JwtConfig();
        jwtConfig.setPrivateKeyPath("/tmp/test-private.pem");
        jwtConfig.setPublicKeyPath("/tmp/test-public.pem");
        jwtConfig.setAccessTokenExpiryHours(24);
        jwtConfig.setRefreshTokenExpiryDays(30);
        jwtConfig.setIssuer("forgelink-idp-test");
        jwtConfig.setKeyId("test-key-1");

        keyService = new KeyService(jwtConfig);
        keyService.init();

        jwtService = new JwtService(jwtConfig, keyService, refreshTokenRepository);
    }

    @Test
    void generateAccessToken_shouldCreateValidToken() {
        // Given
        User user = createTestUser();

        // When
        String token = jwtService.generateAccessToken(user);

        // Then
        assertThat(token).isNotNull();
        assertThat(token.split("\\.")).hasSize(3); // JWT format: header.payload.signature
    }

    @Test
    void validateAccessToken_shouldReturnClaims_forValidToken() {
        // Given
        User user = createTestUser();
        String token = jwtService.generateAccessToken(user);

        // When
        Optional<Claims> claims = jwtService.validateAccessToken(token);

        // Then
        assertThat(claims).isPresent();
        assertThat(claims.get().getSubject()).isEqualTo(user.getId().toString());
        assertThat(claims.get().get("email")).isEqualTo(user.getEmail());
        assertThat(claims.get().get("roles")).isNotNull();
    }

    @Test
    void accessToken_producerContract_usesRolesAsJsonArray() {
        // Pins the producer side of the JWT role-claim contract with Django.
        // If this test changes, services/django-api/apps/core/tests/test_jwt_contract.py
        // must change in lockstep. See also JwtService.generateAccessToken.
        User user = createTestUser();
        String token = jwtService.generateAccessToken(user);

        Claims claims = jwtService.validateAccessToken(token).orElseThrow();

        // Canonical claim name is "roles" (plural), NEVER "role" (singular).
        assertThat(claims).containsKey("roles");
        assertThat(claims).doesNotContainKey("role");

        Object rolesClaim = claims.get("roles");
        // JJWT deserialises a JSON array back to a Collection (List in practice).
        assertThat(rolesClaim).isInstanceOf(Collection.class);
        @SuppressWarnings("unchecked")
        Collection<String> rolesCollection = (Collection<String>) rolesClaim;
        assertThat(rolesCollection).containsExactly("FACTORY_ADMIN");
    }

    @Test
    void accessToken_producerContract_multiRoleUserEmitsAllRoles() {
        // Spring IDP supports multi-role users; the contract emits every role.
        User user = User.builder()
            .id(UUID.randomUUID())
            .email("multi@forgelink.local")
            .passwordHash("$2a$12$test")
            .plantId("steel-plant-kigali")
            .roles(Set.of(Role.PLANT_OPERATOR, Role.TECHNICIAN))
            .enabled(true)
            .locked(false)
            .build();

        String token = jwtService.generateAccessToken(user);
        Claims claims = jwtService.validateAccessToken(token).orElseThrow();

        @SuppressWarnings("unchecked")
        Collection<String> rolesCollection = (Collection<String>) claims.get("roles");
        assertThat(rolesCollection)
            .containsExactlyInAnyOrder("PLANT_OPERATOR", "TECHNICIAN");
    }

    @Test
    void accessToken_producerContract_includesEveryClaimDjangoConsumes() {
        // Freeze the set of claims the Django consumer depends on. See
        // services/django-api/apps/core/tests/test_jwt_contract.py
        // TestClaimShapeFreeze for the matching consumer assertion.
        User user = createTestUser();
        String token = jwtService.generateAccessToken(user);
        Claims claims = jwtService.validateAccessToken(token).orElseThrow();

        List<String> requiredClaims = List.of(
            "sub", "iss", "iat", "exp", "email", "roles", "plant_id"
        );
        for (String claim : requiredClaims) {
            assertThat(claims)
                .as("claim '%s' must be emitted for Django to consume", claim)
                .containsKey(claim);
        }
    }

    @Test
    void validateAccessToken_shouldReturnEmpty_forInvalidToken() {
        // When
        Optional<Claims> claims = jwtService.validateAccessToken("invalid.token.here");

        // Then
        assertThat(claims).isEmpty();
    }

    @Test
    void getJwks_shouldReturnValidJwksFormat() {
        // When
        Map<String, Object> jwks = jwtService.getJwks();

        // Then
        assertThat(jwks).containsKey("keys");
        @SuppressWarnings("unchecked")
        var keys = (java.util.List<Map<String, Object>>) jwks.get("keys");
        assertThat(keys).hasSize(1);

        Map<String, Object> key = keys.get(0);
        assertThat(key.get("kty")).isEqualTo("RSA");
        assertThat(key.get("use")).isEqualTo("sig");
        assertThat(key.get("alg")).isEqualTo("RS256");
        assertThat(key.get("kid")).isEqualTo("test-key-1");
        assertThat(key.get("n")).isNotNull();
        assertThat(key.get("e")).isNotNull();
    }

    private User createTestUser() {
        return User.builder()
            .id(UUID.randomUUID())
            .email("test@forgelink.local")
            .passwordHash("$2a$12$test")
            .firstName("Test")
            .lastName("User")
            .plantId("steel-plant-kigali")
            .roles(Set.of(Role.FACTORY_ADMIN))
            .enabled(true)
            .locked(false)
            .build();
    }
}
