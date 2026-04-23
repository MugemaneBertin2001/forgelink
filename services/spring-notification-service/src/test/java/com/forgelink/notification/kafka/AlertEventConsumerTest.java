package com.forgelink.notification.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.forgelink.notification.dto.AlertEvent;
import com.forgelink.notification.service.EmailNotificationService;
import com.forgelink.notification.service.SlackNotificationService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.mail.MailSendException;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

/**
 * Tests for the AlertEventConsumer dispatch routing.
 *
 * <p>The consumer is the single entry point that turns a Django-emitted
 * alert into one or more external notifications. These tests pin the
 * three contracts a reader has to trust:
 *
 * <ol>
 *   <li>Slack is <b>default-on</b> (null or true) — legacy alert rules
 *       predate the per-rule flag and must keep working.</li>
 *   <li>Email is <b>strictly opt-in</b> — notifyEmail must be true AND
 *       emailRecipients must be non-empty.</li>
 *   <li>Any dispatch failure must propagate so the Kafka message is
 *       NOT acked — duplicate delivery is preferable to silent loss.</li>
 * </ol>
 */
@ExtendWith(MockitoExtension.class)
class AlertEventConsumerTest {

    @Mock
    private SlackNotificationService slackService;

    @Mock
    private EmailNotificationService emailService;

    @Mock
    private Acknowledgment ack;

    private AlertEventConsumer consumer;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        consumer = new AlertEventConsumer(slackService, emailService, objectMapper);
    }

    private AlertEvent.AlertEventBuilder baseEvent() {
        return AlertEvent.builder()
            .alertId("a-123")
            .deviceId("temp-sensor-001")
            .plant("steel-plant-kigali")
            .area("melt-shop")
            .severity("critical")
            .message("overheating")
            .value(1678.4)
            .threshold(1650.0)
            .timestamp(Instant.parse("2026-04-23T09:15:30Z"));
    }

    private ConsumerRecord<String, String> recordFor(AlertEvent event) throws Exception {
        String json = objectMapper.writeValueAsString(event);
        return new ConsumerRecord<>("alerts.notifications", 0, 0L, event.getAlertId(), json);
    }

    // ──────────────────────────────────────────────────────────────
    // Slack channel routing
    // ──────────────────────────────────────────────────────────────

    @Test
    void slackSentWhenNotifySlackTrue() throws Exception {
        AlertEvent event = baseEvent().notifySlack(true).build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(slackService).sendAlert(any(AlertEvent.class));
        verify(ack).acknowledge();
    }

    @Test
    void slackSentWhenNotifySlackNull() throws Exception {
        // Legacy rules emit events with notifySlack unset. Must keep
        // working — this preserved-on-null behaviour is the reason
        // the feature flag was introduced additively.
        AlertEvent event = baseEvent().notifySlack(null).build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(slackService).sendAlert(any(AlertEvent.class));
    }

    @Test
    void slackSkippedWhenNotifySlackFalse() throws Exception {
        AlertEvent event = baseEvent().notifySlack(false).build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(slackService, never()).sendAlert(any(AlertEvent.class));
        verify(ack).acknowledge();
    }

    // ──────────────────────────────────────────────────────────────
    // Email channel routing
    // ──────────────────────────────────────────────────────────────

    @Test
    void emailSentWhenOptedInWithRecipients() throws Exception {
        AlertEvent event = baseEvent()
            .notifySlack(false)
            .notifyEmail(true)
            .emailRecipients(List.of("ops@forgelink.test", "oncall@forgelink.test"))
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        ArgumentCaptor<List<String>> recipientsCaptor = ArgumentCaptor.forClass(List.class);
        verify(emailService).sendAlert(any(AlertEvent.class), recipientsCaptor.capture());
        assertThat(recipientsCaptor.getValue()).hasSize(2);
        verify(ack).acknowledge();
    }

    @Test
    void emailSkippedWhenNotifyEmailNull() throws Exception {
        // Unlike Slack, email is NOT default-on. A null notifyEmail
        // means the rule has not been migrated to email — don't
        // silently start blasting SMTP.
        AlertEvent event = baseEvent()
            .notifyEmail(null)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(emailService, never()).sendAlert(any(AlertEvent.class), any());
    }

    @Test
    void emailSkippedWhenNotifyEmailFalse() throws Exception {
        AlertEvent event = baseEvent()
            .notifyEmail(false)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(emailService, never()).sendAlert(any(AlertEvent.class), any());
    }

    @Test
    void emailSkippedWhenRecipientsEmpty() throws Exception {
        // notifyEmail=true but no recipients configured — still a misfire.
        AlertEvent event = baseEvent()
            .notifyEmail(true)
            .emailRecipients(List.of())
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(emailService, never()).sendAlert(any(AlertEvent.class), any());
    }

    @Test
    void emailSkippedWhenRecipientsNull() throws Exception {
        AlertEvent event = baseEvent()
            .notifyEmail(true)
            .emailRecipients(null)
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(emailService, never()).sendAlert(any(AlertEvent.class), any());
    }

    // ──────────────────────────────────────────────────────────────
    // Fan-out — both channels on one event
    // ──────────────────────────────────────────────────────────────

    @Test
    void bothChannelsInvokedWhenBothOptedIn() throws Exception {
        AlertEvent event = baseEvent()
            .notifySlack(true)
            .notifyEmail(true)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verify(slackService).sendAlert(any(AlertEvent.class));
        verify(emailService).sendAlert(any(AlertEvent.class), any());
        verify(ack).acknowledge();
    }

    @Test
    void noChannelsInvokedWhenAllDisabled() throws Exception {
        AlertEvent event = baseEvent()
            .notifySlack(false)
            .notifyEmail(false)
            .build();
        consumer.consumeAlertEvent(recordFor(event), ack);

        verifyNoInteractions(slackService);
        verifyNoInteractions(emailService);
        // Still ack — this isn't an error, it's a silenced rule.
        verify(ack).acknowledge();
    }

    // ──────────────────────────────────────────────────────────────
    // At-least-once contract — no ack on dispatch failure
    // ──────────────────────────────────────────────────────────────

    @Test
    void noAckWhenSlackThrows() throws Exception {
        doThrow(new RuntimeException("slack 503"))
            .when(slackService).sendAlert(any(AlertEvent.class));

        AlertEvent event = baseEvent().notifySlack(true).build();
        ConsumerRecord<String, String> record = recordFor(event);

        assertThatThrownBy(() -> consumer.consumeAlertEvent(record, ack))
            .isInstanceOf(RuntimeException.class)
            .hasMessageContaining("slack 503");
        verify(ack, never()).acknowledge();
    }

    @Test
    void noAckWhenEmailThrows() throws Exception {
        doThrow(new MailSendException("smtp down"))
            .when(emailService).sendAlert(any(AlertEvent.class), any());

        AlertEvent event = baseEvent()
            .notifySlack(false)
            .notifyEmail(true)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
        ConsumerRecord<String, String> record = recordFor(event);

        assertThatThrownBy(() -> consumer.consumeAlertEvent(record, ack))
            .isInstanceOf(MailSendException.class);
        verify(ack, never()).acknowledge();
    }

    @Test
    void slackFailurePreventsEmailAttempt() throws Exception {
        // Ordering matters: Slack runs first. If it fails, the
        // message is un-acked and will be redelivered — at which
        // point both channels will be retried. We do NOT want
        // email to send twice per retry.
        doThrow(new RuntimeException("slack down"))
            .when(slackService).sendAlert(any(AlertEvent.class));

        AlertEvent event = baseEvent()
            .notifySlack(true)
            .notifyEmail(true)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
        ConsumerRecord<String, String> record = recordFor(event);

        assertThatThrownBy(() -> consumer.consumeAlertEvent(record, ack))
            .isInstanceOf(RuntimeException.class);
        verify(emailService, never()).sendAlert(any(AlertEvent.class), any());
    }

    // ──────────────────────────────────────────────────────────────
    // Payload parsing
    // ──────────────────────────────────────────────────────────────

    @Test
    void malformedJsonPropagatesWithoutAck() {
        ConsumerRecord<String, String> bad = new ConsumerRecord<>(
            "alerts.notifications", 0, 0L, "a-bad", "{not json"
        );

        assertThatThrownBy(() -> consumer.consumeAlertEvent(bad, ack))
            .isInstanceOf(Exception.class);
        verify(ack, never()).acknowledge();
        verifyNoInteractions(slackService);
        verifyNoInteractions(emailService);
    }
}
