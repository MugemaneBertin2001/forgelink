package com.forgelink.notification.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * Health and status endpoints.
 */
@RestController
@Tag(name = "Health", description = "Service health endpoints")
public class HealthController {

    @GetMapping("/")
    @Operation(summary = "Service info")
    public ResponseEntity<Map<String, Object>> info() {
        return ResponseEntity.ok(Map.of(
            "service", "forgelink-notification-service",
            "version", "1.0.0",
            "timestamp", Instant.now().toString()
        ));
    }

    @GetMapping("/health/live")
    @Operation(summary = "Liveness probe")
    public ResponseEntity<Map<String, String>> live() {
        return ResponseEntity.ok(Map.of("status", "UP"));
    }

    @GetMapping("/health/ready")
    @Operation(summary = "Readiness probe")
    public ResponseEntity<Map<String, String>> ready() {
        // Could check Kafka and Slack connectivity here
        return ResponseEntity.ok(Map.of("status", "UP"));
    }
}
