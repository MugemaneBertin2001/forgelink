package com.forgelink.notification.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.forgelink.notification.dto.AlertEvent;
import com.forgelink.notification.service.EmailNotificationService;
import com.forgelink.notification.service.SlackNotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer for alert events from Django.
 *
 * Dispatches each event to every channel the event opts into
 * (notifySlack / notifyEmail). All channels are invoked in sequence;
 * a failure on any channel throws, which leaves the Kafka message
 * un-acked and eligible for redelivery — matching the at-least-once
 * contract we applied to the telemetry consumer.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AlertEventConsumer {

    private final SlackNotificationService slackService;
    private final EmailNotificationService emailService;
    private final ObjectMapper objectMapper;

    @KafkaListener(
        topics = "${kafka.topics.alerts:alerts.notifications}",
        groupId = "${kafka.consumer.group-id:forgelink-notification-service}",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeAlertEvent(ConsumerRecord<String, String> record, Acknowledgment ack) throws Exception {
        log.debug("Received alert event: key={}", record.key());

        AlertEvent event = objectMapper.readValue(record.value(), AlertEvent.class);

        log.info("Processing alert: id={}, severity={}, device={}, slack={}, email={}",
            event.getAlertId(), event.getSeverity(), event.getDeviceId(),
            Boolean.TRUE.equals(event.getNotifySlack()),
            Boolean.TRUE.equals(event.getNotifyEmail()));

        // Slack channel. Default-on when the field is unset to preserve
        // the historical behaviour (before the per-rule flag existed).
        if (event.getNotifySlack() == null || event.getNotifySlack()) {
            slackService.sendAlert(event);
        }

        // Email channel. Strictly opt-in — the rule must have
        // notify_email=true AND a non-empty recipients list.
        if (Boolean.TRUE.equals(event.getNotifyEmail())
                && event.getEmailRecipients() != null
                && !event.getEmailRecipients().isEmpty()) {
            emailService.sendAlert(event, event.getEmailRecipients());
        }

        ack.acknowledge();
    }
}
