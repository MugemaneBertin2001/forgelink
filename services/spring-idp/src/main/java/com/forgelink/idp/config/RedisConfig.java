package com.forgelink.idp.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Redis configuration for refresh token storage.
 */
@Configuration
public class RedisConfig {

    /**
     * ObjectMapper tuned for Redis JSON serialisation.
     *
     * The default {@link GenericJackson2JsonRedisSerializer} constructs its
     * own ObjectMapper that does not know about Java 8 date/time types, so
     * entities like {@code RefreshToken} (which carries {@link java.time.Instant}
     * fields) fail to serialise. Registering {@link JavaTimeModule} and
     * disabling timestamp-style writes emits ISO-8601 strings that round-trip
     * correctly.
     */
    private ObjectMapper redisObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        return mapper;
    }

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        GenericJackson2JsonRedisSerializer valueSerializer =
            new GenericJackson2JsonRedisSerializer(redisObjectMapper());

        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(valueSerializer);
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(valueSerializer);
        template.afterPropertiesSet();
        return template;
    }
}
