package com.forgelink.idp.config;

import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.databind.jsontype.BasicPolymorphicTypeValidator;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Redis configuration for refresh token storage.
 *
 * Two properties must hold for {@link com.forgelink.idp.repository.RefreshTokenRepository}
 * to round-trip a {@link com.forgelink.idp.model.RefreshToken} through Redis:
 *
 * 1. Java 8 date/time types must serialise as ISO-8601 strings
 *    (RefreshToken.issuedAt is a {@link java.time.Instant}).
 * 2. The serialised JSON must carry a polymorphic-type marker (`@class`) so
 *    that {@code Object value = opsForValue().get(key)} deserialises back
 *    to the concrete {@code RefreshToken} type rather than a
 *    {@code LinkedHashMap}; without it, the {@code instanceof RefreshToken}
 *    check in {@code findById} fails and every refresh request is rejected
 *    with "Invalid or expired refresh token".
 *
 * Historically, passing a custom ObjectMapper to
 * {@link GenericJackson2JsonRedisSerializer} disables the default-typing
 * behaviour that the zero-arg constructor enables internally; we have to
 * re-enable it explicitly here.
 */
@Configuration
public class RedisConfig {

    private ObjectMapper redisObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        mapper.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
        // Be lenient on deserialisation: upgrades that add/remove fields
        // on cached DTOs should not break in-flight refresh tokens.
        mapper.configure(
            com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES,
            false
        );

        // Enable default typing so the serialiser writes `@class` type hints
        // and polymorphic reads return the concrete class. The validator
        // limits what can be deserialised to Object subtypes, which is the
        // same level of strictness the default GenericJackson2JsonRedisSerializer
        // applies — sufficient for our internal-only refresh-token cache.
        mapper.activateDefaultTyping(
            BasicPolymorphicTypeValidator.builder().allowIfSubType(Object.class).build(),
            ObjectMapper.DefaultTyping.NON_FINAL,
            JsonTypeInfo.As.PROPERTY
        );
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
