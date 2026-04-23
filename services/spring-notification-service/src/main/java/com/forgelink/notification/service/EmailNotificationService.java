package com.forgelink.notification.service;

import com.forgelink.notification.dto.AlertEvent;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;

import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.List;

/**
 * SMTP email dispatcher for ForgeLink alerts.
 *
 * Runs alongside {@link SlackNotificationService}; both are invoked
 * from {@link com.forgelink.notification.kafka.AlertEventConsumer}
 * based on the per-alert channel flags. A failure here throws the
 * original exception so the Kafka consumer does not ack the message
 * — the at-least-once redelivery contract of the notification
 * pipeline mirrors the one applied to the telemetry consumer.
 *
 * SMTP connection is configured via Spring Boot's standard
 * {@code spring.mail.*} properties; in dev we point at Mailhog,
 * in production at a provider like Postmark. See
 * {@code application.yml}.
 */
@Service
@Slf4j
public class EmailNotificationService {

    private static final DateTimeFormatter TIME_FORMAT =
        DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss z");

    private final JavaMailSender mailSender;
    private final String fromAddress;
    private final String plantTimezone;

    public EmailNotificationService(
            JavaMailSender mailSender,
            @Value("${spring.mail.from:alerts@forgelink.local}") String fromAddress,
            @Value("${forgelink.timezone:Africa/Kigali}") String timezone) {
        this.mailSender = mailSender;
        this.fromAddress = fromAddress;
        this.plantTimezone = timezone;
    }

    public void sendAlert(AlertEvent event, List<String> recipients) throws MessagingException, MailException {
        if (recipients == null || recipients.isEmpty()) {
            log.debug(
                "Email dispatch skipped for alert {}: no recipients set",
                event.getAlertId()
            );
            return;
        }

        MimeMessage message = mailSender.createMimeMessage();
        MimeMessageHelper helper = new MimeMessageHelper(message, false, "UTF-8");

        helper.setFrom(fromAddress);
        helper.setTo(recipients.toArray(new String[0]));
        helper.setSubject(buildSubject(event));
        helper.setText(buildBody(event), /* html */ false);

        mailSender.send(message);

        log.info(
            "Email dispatched: alertId={} severity={} recipients={}",
            event.getAlertId(), event.getSeverity(), recipients.size()
        );
    }

    private String buildSubject(AlertEvent event) {
        String severity = event.getSeverity() == null
            ? "ALERT" : event.getSeverity().toUpperCase();
        String device = event.getDeviceId() == null ? "-" : event.getDeviceId();
        return String.format("[%s] %s — %s", severity, device, event.getMessage());
    }

    private String buildBody(AlertEvent event) {
        StringBuilder sb = new StringBuilder();
        sb.append("ForgeLink Alert\n\n");
        sb.append("Device:   ").append(defaultText(event.getDeviceId())).append("\n");
        if (event.getDeviceName() != null) {
            sb.append("Name:     ").append(event.getDeviceName()).append("\n");
        }
        sb.append("Area:     ").append(defaultText(event.getArea())).append("\n");
        sb.append("Plant:    ").append(defaultText(event.getPlant())).append("\n");
        sb.append("Severity: ").append(defaultText(event.getSeverity())).append("\n");
        sb.append("Type:     ").append(defaultText(event.getAlertType())).append("\n\n");
        sb.append("Message:  ").append(event.getMessage()).append("\n\n");

        if (event.getValue() != null) {
            sb.append(String.format("Value:    %.2f", event.getValue()));
            if (event.getUnit() != null && !event.getUnit().isEmpty()) {
                sb.append(" ").append(event.getUnit());
            }
            sb.append("\n");
        }
        if (event.getThreshold() != null) {
            sb.append(String.format("Threshold: %.2f", event.getThreshold()));
            if (event.getUnit() != null && !event.getUnit().isEmpty()) {
                sb.append(" ").append(event.getUnit());
            }
            sb.append("\n");
        }
        if (event.getTimestamp() != null) {
            sb.append("Time:     ").append(
                event.getTimestamp().atZone(ZoneId.of(plantTimezone)).format(TIME_FORMAT)
            ).append("\n");
        }
        sb.append("\nAlert ID: ").append(event.getAlertId()).append("\n");
        return sb.toString();
    }

    private String defaultText(String v) {
        return (v == null || v.isEmpty()) ? "-" : v;
    }
}
