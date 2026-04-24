package com.forgelink.notification.logging;

/**
 * Shared constants for correlation-ID propagation across this service.
 *
 * <p>The header name matches what Django's CorrelationIdMiddleware emits
 * (both as an HTTP header on REST responses and as a Kafka message
 * header on outbound alert events). Keep the bytes identical or the
 * notification service will mint fresh IDs and break the cross-service
 * trace.
 */
public final class CorrelationId {

    /** HTTP + Kafka header name; lower-case to match Django's bytes. */
    public static final String HEADER = "x-correlation-id";

    /** SLF4J MDC key. Read in logback-spring.xml's pattern layout. */
    public static final String MDC_KEY = "correlation_id";

    private CorrelationId() {}
}
