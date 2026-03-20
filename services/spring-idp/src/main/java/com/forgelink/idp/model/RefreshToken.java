package com.forgelink.idp.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.Instant;
import java.util.Set;
import java.util.UUID;

/**
 * Refresh token stored in Redis.
 * Used to issue new access tokens without re-authentication.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RefreshToken implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * Unique token identifier.
     */
    private String tokenId;

    /**
     * User ID this token belongs to.
     */
    private UUID userId;

    /**
     * User email for convenience.
     */
    private String email;

    /**
     * User roles at time of token issuance.
     */
    private Set<String> roles;

    /**
     * Plant ID if applicable.
     */
    private String plantId;

    /**
     * When the token was issued.
     */
    private Instant issuedAt;

    /**
     * When the token expires.
     */
    private Instant expiresAt;

    /**
     * IP address where token was issued.
     */
    private String issuedFromIp;

    /**
     * User agent of the client.
     */
    private String userAgent;

    /**
     * Check if token is expired.
     */
    public boolean isExpired() {
        return Instant.now().isAfter(expiresAt);
    }
}
