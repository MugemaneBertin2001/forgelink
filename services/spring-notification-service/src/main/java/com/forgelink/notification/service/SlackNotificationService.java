package com.forgelink.notification.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.forgelink.notification.dto.AlertEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

/**
 * Slack webhook notification service for ForgeLink alerts.
 * Uses simple HTTP POST to Slack incoming webhook.
 */
@Service
@Slf4j
public class SlackNotificationService {

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String webhookUrl;
    private final String plantTimezone;

    private static final DateTimeFormatter TIME_FORMAT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    public SlackNotificationService(
            @Value("${slack.webhook-url}") String webhookUrl,
            @Value("${forgelink.timezone:Africa/Kigali}") String timezone,
            ObjectMapper objectMapper) {

        this.webhookUrl = webhookUrl;
        this.plantTimezone = timezone;
        this.objectMapper = objectMapper;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    public void sendAlert(AlertEvent event) {
        try {
            String payload = buildSlackPayload(event);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(webhookUrl))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(payload))
                .timeout(Duration.ofSeconds(30))
                .build();

            HttpResponse<String> response = httpClient.send(request,
                HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                log.info("Slack notification sent: alertId={}, device={}",
                    event.getAlertId(), event.getDeviceId());
            } else {
                log.error("Slack webhook error: status={}, body={}",
                    response.statusCode(), response.body());
            }

        } catch (Exception e) {
            log.error("Failed to send Slack notification: {}", e.getMessage(), e);
        }
    }

    private String buildSlackPayload(AlertEvent event) throws Exception {
        String emoji = getSeverityEmoji(event.getSeverity());
        String timestamp = event.getTimestamp() != null
            ? event.getTimestamp().atZone(ZoneId.of(plantTimezone)).format(TIME_FORMAT)
            : "N/A";

        // Build message text
        StringBuilder text = new StringBuilder();
        text.append(emoji).append(" *").append(event.getSeverity().toUpperCase()).append(" ALERT*\n\n");
        text.append("*").append(event.getMessage()).append("*\n\n");
        text.append("• *Device:* ").append(event.getDeviceId()).append("\n");
        text.append("• *Area:* ").append(event.getArea()).append("\n");
        text.append("• *Plant:* ").append(event.getPlant()).append("\n");

        if (event.getValue() != null) {
            text.append("• *Value:* ").append(String.format("%.2f", event.getValue()));
            if (event.getUnit() != null) {
                text.append(" ").append(event.getUnit());
            }
            if (event.getThreshold() != null) {
                text.append(" (threshold: ").append(String.format("%.2f", event.getThreshold())).append(")");
            }
            text.append("\n");
        }

        text.append("• *Time:* ").append(timestamp).append(" (").append(plantTimezone).append(")\n");
        text.append("• *Alert ID:* `").append(event.getAlertId()).append("`");

        Map<String, String> payload = new HashMap<>();
        payload.put("text", text.toString());

        return objectMapper.writeValueAsString(payload);
    }

    private String getSeverityEmoji(String severity) {
        if (severity == null) return ":bell:";
        return switch (severity.toLowerCase()) {
            case "critical" -> ":rotating_light:";
            case "high" -> ":warning:";
            case "medium" -> ":large_orange_diamond:";
            case "low" -> ":information_source:";
            default -> ":bell:";
        };
    }
}
