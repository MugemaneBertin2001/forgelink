package com.forgelink.idp.logging;

/**
 * Shared constants for correlation-ID propagation across this service.
 *
 * <p>The header name matches what Django's CorrelationIdMiddleware emits.
 * Keep the two strings identical or the trace breaks across the
 * Django → IDP JWT-refresh round-trip.
 */
public final class CorrelationId {

    public static final String HEADER = "X-Correlation-ID";
    public static final String MDC_KEY = "correlation_id";

    private CorrelationId() {}
}
