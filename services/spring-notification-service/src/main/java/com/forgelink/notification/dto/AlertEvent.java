package com.forgelink.notification.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;
import java.util.List;

/**
 * Alert event received from Django via Kafka.
 *
 * The channel-selection fields (notifySlack, notifyEmail,
 * emailRecipients, slackChannel) mirror the AlertRule columns on the
 * Django side and are what the consumer uses to decide which
 * dispatcher(s) to invoke. A field left null / empty disables that
 * channel for the event.
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

    // Channel routing
    private Boolean notifySlack;
    private String slackChannel;   // Target Slack channel; null = use default

    private Boolean notifyEmail;
    private List<String> emailRecipients;
}
