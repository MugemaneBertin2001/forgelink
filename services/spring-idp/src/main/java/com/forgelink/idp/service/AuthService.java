package com.forgelink.idp.service;

import com.forgelink.idp.dto.AuthResponse;
import com.forgelink.idp.dto.LoginRequest;
import com.forgelink.idp.dto.RefreshRequest;
import com.forgelink.idp.exception.AuthenticationException;
import com.forgelink.idp.exception.UserLockedException;
import com.forgelink.idp.model.RefreshToken;
import com.forgelink.idp.model.User;
import com.forgelink.idp.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.time.temporal.ChronoUnit;

/**
 * Service for authentication operations.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class AuthService {

    private static final int MAX_FAILED_ATTEMPTS = 5;
    private static final int LOCKOUT_MINUTES = 30;

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    /**
     * Authenticate user with email and password.
     */
    @Transactional
    public AuthResponse login(LoginRequest request, String ipAddress, String userAgent) {
        // Find user
        User user = userRepository.findByEmailIgnoreCase(request.getEmail())
            .orElseThrow(() -> new AuthenticationException("Invalid email or password"));

        // Check if locked
        if (user.isLockedOut()) {
            throw new UserLockedException("Account is locked. Try again later.");
        }

        // Check if enabled
        if (!user.isEnabled()) {
            throw new AuthenticationException("Account is disabled");
        }

        // Verify password
        if (!passwordEncoder.matches(request.getPassword(), user.getPasswordHash())) {
            handleFailedLogin(user);
            throw new AuthenticationException("Invalid email or password");
        }

        // Successful login
        userRepository.updateLastLogin(user.getId(), Instant.now(), ipAddress);

        // Generate tokens
        String accessToken = jwtService.generateAccessToken(user);
        RefreshToken refreshToken = jwtService.generateRefreshToken(user, ipAddress, userAgent);

        log.info("User {} logged in from {}", user.getEmail(), ipAddress);

        return AuthResponse.builder()
            .accessToken(accessToken)
            .refreshToken(refreshToken.getTokenId())
            .tokenType("Bearer")
            .expiresIn(jwtService.validateAccessToken(accessToken)
                .map(claims -> claims.getExpiration().getTime() / 1000 - Instant.now().getEpochSecond())
                .orElse(0L))
            .build();
    }

    /**
     * Refresh access token using refresh token.
     */
    @Transactional
    public AuthResponse refresh(RefreshRequest request, String ipAddress, String userAgent) {
        // Validate refresh token
        RefreshToken refreshToken = jwtService.validateRefreshToken(request.getRefreshToken())
            .orElseThrow(() -> new AuthenticationException("Invalid or expired refresh token"));

        // Get user
        User user = userRepository.findById(refreshToken.getUserId())
            .orElseThrow(() -> new AuthenticationException("User not found"));

        // Check if user is still active
        if (!user.isEnabled() || user.isLockedOut()) {
            jwtService.revokeRefreshToken(refreshToken.getTokenId());
            throw new AuthenticationException("Account is disabled or locked");
        }

        // Revoke old refresh token (rotation)
        jwtService.revokeRefreshToken(refreshToken.getTokenId());

        // Generate new tokens
        String accessToken = jwtService.generateAccessToken(user);
        RefreshToken newRefreshToken = jwtService.generateRefreshToken(user, ipAddress, userAgent);

        log.debug("Refreshed tokens for user {}", user.getEmail());

        return AuthResponse.builder()
            .accessToken(accessToken)
            .refreshToken(newRefreshToken.getTokenId())
            .tokenType("Bearer")
            .expiresIn(jwtService.validateAccessToken(accessToken)
                .map(claims -> claims.getExpiration().getTime() / 1000 - Instant.now().getEpochSecond())
                .orElse(0L))
            .build();
    }

    /**
     * Logout user by revoking refresh token.
     */
    @Transactional
    public void logout(String refreshToken) {
        jwtService.revokeRefreshToken(refreshToken);
        log.debug("User logged out, refresh token revoked");
    }

    /**
     * Handle failed login attempt.
     */
    private void handleFailedLogin(User user) {
        userRepository.incrementFailedAttempts(user.getId());

        if (user.getFailedLoginAttempts() + 1 >= MAX_FAILED_ATTEMPTS) {
            Instant lockUntil = Instant.now().plus(LOCKOUT_MINUTES, ChronoUnit.MINUTES);
            userRepository.lockUser(user.getId(), lockUntil);
            log.warn("User {} locked due to too many failed attempts", user.getEmail());
        }
    }
}
