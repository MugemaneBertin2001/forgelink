package com.forgelink.notification.service;

import com.forgelink.notification.dto.AlertEvent;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;

import java.time.Instant;
import java.util.List;
import java.util.Properties;

import jakarta.mail.Session;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link EmailNotificationService}. We verify the
 * dispatch happens-or-not contract (which is what the Kafka
 * consumer's at-least-once semantics rely on) and the message
 * contents for a canonical AlertEvent. The wire-level SMTP path is
 * exercised by integration tests against Mailhog.
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class EmailNotificationServiceTest {

    @Mock
    private JavaMailSender mailSender;

    private EmailNotificationService service;

    @BeforeEach
    void setUp() {
        service = new EmailNotificationService(
            mailSender,
            "alerts@forgelink.test",
            "Africa/Kigali"
        );
        // JavaMailSender needs a real MimeMessage (not a mock) for the
        // MimeMessageHelper that the service uses; construct one from a
        // no-arg Session so no actual SMTP connection is attempted.
        when(mailSender.createMimeMessage())
            .thenReturn(new MimeMessage(Session.getInstance(new Properties())));
    }

    private AlertEvent buildEvent() {
        return AlertEvent.builder()
            .alertId("a-123")
            .deviceId("temp-sensor-001")
            .deviceName("EAF-1 Electrode A Temperature")
            .plant("steel-plant-kigali")
            .area("melt-shop")
            .alertType("threshold_high")
            .severity("critical")
            .message("Temperature exceeded 1650°C")
            .value(1678.4)
            .threshold(1650.0)
            .unit("celsius")
            .timestamp(Instant.parse("2026-04-23T09:15:30Z"))
            .notifyEmail(true)
            .emailRecipients(List.of("ops@forgelink.test"))
            .build();
    }

    @Test
    void sendAlert_sendsMessageToRecipients() throws Exception {
        service.sendAlert(buildEvent(), List.of("ops@forgelink.test", "oncall@forgelink.test"));

        ArgumentCaptor<MimeMessage> captor = ArgumentCaptor.forClass(MimeMessage.class);
        verify(mailSender).send(captor.capture());
        MimeMessage sent = captor.getValue();

        // Subject encodes severity and device
        assertThat(sent.getSubject()).contains("CRITICAL");
        assertThat(sent.getSubject()).contains("temp-sensor-001");
        // Recipients match
        assertThat(sent.getAllRecipients()).hasSize(2);
        // Body contains the key alert facts
        String body = (String) sent.getContent();
        assertThat(body).contains("temp-sensor-001");
        assertThat(body).contains("steel-plant-kigali");
        assertThat(body).contains("melt-shop");
        assertThat(body).contains("1678.40");
        assertThat(body).contains("1650.00");
        assertThat(body).contains("a-123");
    }

    @Test
    void sendAlert_skipsDispatchWhenRecipientsEmpty() throws MessagingException {
        service.sendAlert(buildEvent(), List.of());
        verify(mailSender, never()).send(any(MimeMessage.class));
    }

    @Test
    void sendAlert_skipsDispatchWhenRecipientsNull() throws MessagingException {
        service.sendAlert(buildEvent(), null);
        verify(mailSender, never()).send(any(MimeMessage.class));
    }

    @Test
    void sendAlert_propagatesSmtpFailure() {
        // If SMTP throws, the exception must bubble up so the Kafka
        // consumer does NOT ack the message — the redelivery contract
        // is the whole point of at-least-once notification dispatch.
        doThrow(new MailSendException("SMTP connection refused"))
            .when(mailSender).send(any(MimeMessage.class));

        assertThatThrownBy(() ->
            service.sendAlert(buildEvent(), List.of("ops@forgelink.test"))
        ).isInstanceOf(MailSendException.class)
         .hasMessageContaining("connection refused");
    }
}
