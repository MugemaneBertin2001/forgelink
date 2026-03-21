package com.forgelink.notification.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * Alert event received from Django via Kafka.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertEvent {

    private String alertId;
    private String deviceId;
    private String deviceName;
    private String plant;
    private String area;
    private String alertType;      // threshold_high, threshold_low, device_fault, etc.
    private String severity;       // critical, high, medium, low, info
    private String message;
    private Double value;
    private Double threshold;
    private String unit;
    private Instant timestamp;
    private String slackChannel;   // Target Slack channel
}
