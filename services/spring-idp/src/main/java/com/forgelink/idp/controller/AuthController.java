package com.forgelink.idp.controller;

import com.forgelink.idp.dto.*;
import com.forgelink.idp.service.AuthService;
import com.forgelink.idp.service.JwtService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashSet;
import java.util.List;
import java.util.Map;

/**
 * Authentication controller for ForgeLink IDP.
 */
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Authentication", description = "Authentication and token management")
public class AuthController {

    private final AuthService authService;
    private final JwtService jwtService;

    @PostMapping("/login")
    @Operation(summary = "Login with email and password")
    public ResponseEntity<AuthResponse> login(
            @Valid @RequestBody LoginRequest request,
            HttpServletRequest httpRequest) {

        String ipAddress = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");

        AuthResponse response = authService.login(request, ipAddress, userAgent);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/refresh")
    @Operation(summary = "Refresh access token using refresh token")
    public ResponseEntity<AuthResponse> refresh(
            @Valid @RequestBody RefreshRequest request,
            HttpServletRequest httpRequest) {

        String ipAddress = getClientIp(httpRequest);
        String userAgent = httpRequest.getHeader("User-Agent");

        AuthResponse response = authService.refresh(request, ipAddress, userAgent);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    @Operation(summary = "Logout and revoke refresh token")
    public ResponseEntity<Map<String, String>> logout(
            @Valid @RequestBody LogoutRequest request) {

        authService.logout(request.getRefreshToken());
        return ResponseEntity.ok(Map.of("message", "Logged out successfully"));
    }

    @GetMapping("/jwks")
    @Operation(summary = "Get JSON Web Key Set for token verification")
    public ResponseEntity<Map<String, Object>> getJwks() {
        return ResponseEntity.ok(jwtService.getJwks());
    }

    @GetMapping("/validate")
    @Operation(summary = "Validate and introspect an access token")
    public ResponseEntity<TokenValidationResponse> validateToken(
            @RequestHeader("Authorization") String authHeader) {

        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return ResponseEntity.ok(TokenValidationResponse.builder()
                .active(false)
                .build());
        }

        String token = authHeader.substring(7);

        return jwtService.validateAccessToken(token)
            .map(claims -> {
                @SuppressWarnings("unchecked")
                List<String> rolesList = claims.get("roles", List.class);

                return ResponseEntity.ok(TokenValidationResponse.builder()
                    .active(true)
                    .sub(claims.getSubject())
                    .email(claims.get("email", String.class))
                    .roles(rolesList != null ? new HashSet<>(rolesList) : new HashSet<>())
                    .plantId(claims.get("plant_id", String.class))
                    .exp(claims.getExpiration().getTime() / 1000)
                    .iat(claims.getIssuedAt().getTime() / 1000)
                    .iss(claims.getIssuer())
                    .build());
            })
            .orElse(ResponseEntity.ok(TokenValidationResponse.builder()
                .active(false)
                .build()));
    }

    private String getClientIp(HttpServletRequest request) {
        String xForwardedFor = request.getHeader("X-Forwarded-For");
        if (xForwardedFor != null && !xForwardedFor.isEmpty()) {
            return xForwardedFor.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }
}
