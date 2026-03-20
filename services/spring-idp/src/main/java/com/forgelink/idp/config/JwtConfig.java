package com.forgelink.idp.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * JWT configuration properties.
 */
@Configuration
@ConfigurationProperties(prefix = "jwt")
@Data
public class JwtConfig {

    /**
     * Path to the RSA private key (PEM format).
     */
    private String privateKeyPath;

    /**
     * Path to the RSA public key (PEM format).
     */
    private String publicKeyPath;

    /**
     * Access token expiry in hours.
     */
    private int accessTokenExpiryHours = 24;

    /**
     * Refresh token expiry in days.
     */
    private int refreshTokenExpiryDays = 30;

    /**
     * JWT issuer claim.
     */
    private String issuer = "forgelink-idp";

    /**
     * Key ID for JWKS.
     */
    private String keyId = "forgelink-key-1";
}
