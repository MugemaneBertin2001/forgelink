package com.forgelink.idp.service;

import com.forgelink.idp.config.JwtConfig;
import com.forgelink.idp.model.RefreshToken;
import com.forgelink.idp.model.Role;
import com.forgelink.idp.model.User;
import com.forgelink.idp.repository.RefreshTokenRepository;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Service for JWT token generation and validation.
 * Uses RS256 (RSA with SHA-256) for signing.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class JwtService {

    private final JwtConfig jwtConfig;
    private final KeyService keyService;
    private final RefreshTokenRepository refreshTokenRepository;

    /**
     * Generate an access token for a user.
     */
    public String generateAccessToken(User user) {
        Instant now = Instant.now();
        Instant expiry = now.plusSeconds(jwtConfig.getAccessTokenExpiryHours() * 3600L);

        Set<String> roleNames = user.getRoles().stream()
            .map(Role::name)
            .collect(Collectors.toSet());

        return Jwts.builder()
            .header()
                .keyId(keyService.getKeyId())
                .type("JWT")
                .and()
            .subject(user.getId().toString())
            .issuer(jwtConfig.getIssuer())
            .issuedAt(Date.from(now))
            .expiration(Date.from(expiry))
            .claim("email", user.getEmail())
            .claim("name", user.getFullName())
            .claim("roles", roleNames)
            .claim("plant_id", user.getPlantId())
            .signWith(keyService.getPrivateKey())
            .compact();
    }

    /**
     * Generate a refresh token for a user.
     */
    public RefreshToken generateRefreshToken(User user, String ipAddress, String userAgent) {
        Instant now = Instant.now();
        Duration ttl = Duration.ofDays(jwtConfig.getRefreshTokenExpiryDays());
        Instant expiry = now.plus(ttl);

        Set<String> roleNames = user.getRoles().stream()
            .map(Role::name)
            .collect(Collectors.toSet());

        RefreshToken token = RefreshToken.builder()
            .tokenId(UUID.randomUUID().toString())
            .userId(user.getId())
            .email(user.getEmail())
            .roles(roleNames)
            .plantId(user.getPlantId())
            .issuedAt(now)
            .expiresAt(expiry)
            .issuedFromIp(ipAddress)
            .userAgent(userAgent)
            .build();

        refreshTokenRepository.save(token, ttl);
        log.debug("Generated refresh token for user {}", user.getEmail());

        return token;
    }

    /**
     * Validate and parse an access token.
     */
    public Optional<Claims> validateAccessToken(String token) {
        try {
            Claims claims = Jwts.parser()
                .verifyWith(keyService.getPublicKey())
                .build()
                .parseSignedClaims(token)
                .getPayload();

            return Optional.of(claims);
        } catch (Exception e) {
            log.debug("Token validation failed: {}", e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Validate a refresh token.
     */
    public Optional<RefreshToken> validateRefreshToken(String tokenId) {
        // Check blacklist
        if (refreshTokenRepository.isBlacklisted(tokenId)) {
            log.debug("Refresh token {} is blacklisted", tokenId);
            return Optional.empty();
        }

        // Find and validate
        return refreshTokenRepository.findById(tokenId)
            .filter(token -> !token.isExpired());
    }

    /**
     * Revoke a refresh token.
     */
    public void revokeRefreshToken(String tokenId) {
        Duration remainingTtl = Duration.ofDays(jwtConfig.getRefreshTokenExpiryDays());
        refreshTokenRepository.blacklist(tokenId, remainingTtl);
        refreshTokenRepository.deleteById(tokenId);
        log.info("Revoked refresh token {}", tokenId);
    }

    /**
     * Revoke all refresh tokens for a user.
     */
    public void revokeAllUserTokens(UUID userId) {
        refreshTokenRepository.deleteAllByUserId(userId);
        log.info("Revoked all refresh tokens for user {}", userId);
    }

    /**
     * Get JWKS (JSON Web Key Set) for public key distribution.
     */
    public Map<String, Object> getJwks() {
        var publicKey = keyService.getPublicKey();

        Map<String, Object> jwk = new LinkedHashMap<>();
        jwk.put("kty", "RSA");
        jwk.put("use", "sig");
        jwk.put("alg", "RS256");
        jwk.put("kid", keyService.getKeyId());
        jwk.put("n", Base64.getUrlEncoder().withoutPadding()
            .encodeToString(publicKey.getModulus().toByteArray()));
        jwk.put("e", Base64.getUrlEncoder().withoutPadding()
            .encodeToString(publicKey.getPublicExponent().toByteArray()));

        Map<String, Object> jwks = new LinkedHashMap<>();
        jwks.put("keys", List.of(jwk));

        return jwks;
    }
}
