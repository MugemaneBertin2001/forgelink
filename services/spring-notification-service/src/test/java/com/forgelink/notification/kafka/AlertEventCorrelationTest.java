package com.forgelink.notification.kafka;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.forgelink.notification.dto.AlertEvent;
import com.forgelink.notification.logging.CorrelationId;
import com.forgelink.notification.service.EmailNotificationService;
import com.forgelink.notification.service.SlackNotificationService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.common.header.internals.RecordHeader;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.slf4j.MDC;
import org.springframework.kafka.support.Acknowledgment;

import java.nio.charset.StandardCharsets;
import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;

/**
 * Tests that correlation-ID propagation from the Kafka header into
 * SLF4J MDC actually happens around every dispatch.
 *
 * <p>The dispatch-routing behaviour is covered separately in
 * {@link AlertEventConsumerTest}; these tests focus solely on the
 * MDC contract, which is what makes a single alert greppable across
 * slack/email service logs.
 */
@ExtendWith(MockitoExtension.class)
class AlertEventCorrelationTest {

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
        MDC.clear();
    }

    private static AlertEvent baseEvent() {
        return AlertEvent.builder()
            .alertId("a-123")
            .deviceId("temp-sensor-001")
            .severity("critical")
            .message("overheat")
            .timestamp(Instant.parse("2026-04-23T09:15:30Z"))
            .notifySlack(true)
            .build();
    }

    private ConsumerRecord<String, String> record(AlertEvent event, String correlationId)
            throws Exception {
        String json = objectMapper.writeValueAsString(event);
        ConsumerRecord<String, String> r =
            new ConsumerRecord<>("alerts.notifications", 0, 0L, event.getAlertId(), json);
        if (correlationId != null) {
            r.headers().add(new RecordHeader(
                CorrelationId.HEADER,
                correlationId.getBytes(StandardCharsets.UTF_8)
            ));
        }
        return r;
    }

    @Test
    void propagatesHeaderIntoMdcDuringDispatch() throws Exception {
        String incoming = "deadbeef-0000-0000-0000-000000000000";
        String[] observedDuringDispatch = {null};

        doAnswer(inv -> {
            observedDuringDispatch[0] = MDC.get(CorrelationId.MDC_KEY);
            return null;
        }).when(slackService).sendAlert(any(AlertEvent.class));

        consumer.consumeAlertEvent(record(baseEvent(), incoming), ack);

        assertThat(observedDuringDispatch[0]).isEqualTo(incoming);
    }

    @Test
    void mintsFreshIdWhenHeaderMissing() throws Exception {
        String[] observed = {null};
        doAnswer(inv -> {
            observed[0] = MDC.get(CorrelationId.MDC_KEY);
            return null;
        }).when(slackService).sendAlert(any(AlertEvent.class));

        consumer.consumeAlertEvent(record(baseEvent(), null), ack);

        // A UUID string is 36 characters with 4 hyphens.
        assertThat(observed[0]).isNotNull();
        assertThat(observed[0]).hasSize(36);
        assertThat(observed[0].chars().filter(c -> c == '-').count()).isEqualTo(4);
    }

    @Test
    void clearsMdcAfterDispatch() throws Exception {
        String incoming = "11111111-2222-3333-4444-555555555555";
        consumer.consumeAlertEvent(record(baseEvent(), incoming), ack);

        // The finally-block in the consumer must clear MDC so the next
        // message on the same thread doesn't inherit this one's ID.
        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
    }

    @Test
    void clearsMdcEvenWhenDispatchThrows() throws Exception {
        doAnswer(inv -> {
            throw new RuntimeException("slack down");
        }).when(slackService).sendAlert(any(AlertEvent.class));

        try {
            consumer.consumeAlertEvent(record(baseEvent(), "aaaa"), ack);
        } catch (RuntimeException ignored) {
            // Expected — dispatch failure propagates so Kafka doesn't ack.
        }
        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
    }
}
