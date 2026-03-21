package com.forgelink.notification;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * ForgeLink Notification Service.
 *
 * Consumes alert events from Kafka and dispatches notifications via:
 * - Firebase Cloud Messaging (FCM) for mobile push
 * - Email (SMTP)
 * - SMS (future)
 *
 * This service does NOT own any business data.
 * Django is the source of truth for alerts and users.
 */
@SpringBootApplication
@EnableAsync
public class NotificationServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(NotificationServiceApplication.class, args);
    }
}
