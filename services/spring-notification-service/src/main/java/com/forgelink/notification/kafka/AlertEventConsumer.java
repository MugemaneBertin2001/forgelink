package com.forgelink.notification.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.forgelink.notification.dto.AlertEvent;
import com.forgelink.notification.service.SlackNotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer for alert events from Django.
 * Dispatches notifications to Slack.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class AlertEventConsumer {

    private final SlackNotificationService slackService;
    private final ObjectMapper objectMapper;

    @KafkaListener(
        topics = "${kafka.topics.alerts:alerts.notifications}",
        groupId = "${kafka.consumer.group-id:forgelink-notification-service}",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consumeAlertEvent(ConsumerRecord<String, String> record, Acknowledgment ack) {
        log.debug("Received alert event: key={}", record.key());

        try {
            AlertEvent event = objectMapper.readValue(record.value(), AlertEvent.class);

            log.info("Processing alert: id={}, severity={}, device={}",
                event.getAlertId(), event.getSeverity(), event.getDeviceId());

            slackService.sendAlert(event);
            ack.acknowledge();

        } catch (Exception e) {
            log.error("Failed to process alert event: {}", e.getMessage(), e);
        }
    }
}
