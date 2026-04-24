package com.forgelink.idp.logging;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.slf4j.MDC;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;

import java.io.IOException;
import java.util.UUID;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests for {@link CorrelationIdFilter} — HTTP path of the
 * cross-service tracing story.
 *
 * <p>The filter is the Spring IDP's equivalent of Django's
 * CorrelationIdMiddleware: incoming X-Correlation-ID is reused,
 * missing → minted fresh, and the value is bound to SLF4J MDC for
 * the duration of the filter chain (cleared after — servlet threads
 * are pooled).
 */
class CorrelationIdFilterTest {

    private CorrelationIdFilter filter;

    @BeforeEach
    void setUp() {
        filter = new CorrelationIdFilter();
        MDC.clear();
    }

    @AfterEach
    void tearDown() {
        MDC.clear();
    }

    @Test
    void reusesIncomingHeaderAsMdcValue() throws ServletException, IOException {
        String incoming = "11111111-2222-3333-4444-555555555555";
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader(CorrelationId.HEADER, incoming);

        String[] observedDuringChain = {null};
        FilterChain chain = (req, res) -> {
            observedDuringChain[0] = MDC.get(CorrelationId.MDC_KEY);
        };

        filter.doFilter(request, response, chain);

        assertThat(observedDuringChain[0]).isEqualTo(incoming);
        assertThat(response.getHeader(CorrelationId.HEADER)).isEqualTo(incoming);
    }

    @Test
    void generatesUuidWhenHeaderMissing() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();

        String[] observed = {null};
        FilterChain chain = (req, res) -> {
            observed[0] = MDC.get(CorrelationId.MDC_KEY);
        };

        filter.doFilter(request, response, chain);

        assertThat(observed[0]).isNotNull();
        UUID parsed = UUID.fromString(observed[0]);
        assertThat(parsed.version()).isEqualTo(4);
        assertThat(response.getHeader(CorrelationId.HEADER)).isEqualTo(observed[0]);
    }

    @Test
    void generatesUuidWhenHeaderBlank() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader(CorrelationId.HEADER, "   ");

        String[] observed = {null};
        FilterChain chain = (req, res) -> {
            observed[0] = MDC.get(CorrelationId.MDC_KEY);
        };

        filter.doFilter(request, response, chain);

        assertThat(observed[0]).isNotBlank();
        // The minted ID must NOT be the whitespace the client sent.
        assertThat(observed[0]).isNotEqualTo("   ");
    }

    @Test
    void clearsMdcAfterFilterChain() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader(CorrelationId.HEADER, "some-id");

        filter.doFilter(request, response, Mockito.mock(FilterChain.class));

        // Servlet threads are pooled — the next request on this
        // thread must not inherit this one's ID.
        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
    }

    @Test
    void clearsMdcEvenWhenChainThrows() throws ServletException, IOException {
        MockHttpServletRequest request = new MockHttpServletRequest();
        MockHttpServletResponse response = new MockHttpServletResponse();
        request.addHeader(CorrelationId.HEADER, "some-id");

        FilterChain angryChain = (req, res) -> {
            throw new ServletException("downstream boom");
        };

        try {
            filter.doFilter(request, response, angryChain);
        } catch (ServletException ignored) {
            // expected
        }
        assertThat(MDC.get(CorrelationId.MDC_KEY)).isNull();
    }
}
