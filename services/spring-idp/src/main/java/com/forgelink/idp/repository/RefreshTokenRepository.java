package com.forgelink.idp.repository;

import com.forgelink.idp.model.RefreshToken;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

import java.time.Duration;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Redis repository for refresh tokens.
 */
@Repository
@RequiredArgsConstructor
@Slf4j
public class RefreshTokenRepository {

    private static final String TOKEN_KEY_PREFIX = "refresh_token:";
    private static final String USER_TOKENS_KEY_PREFIX = "user_tokens:";
    private static final String BLACKLIST_KEY_PREFIX = "blacklist:";

    private final RedisTemplate<String, Object> redisTemplate;

    /**
     * Save a refresh token.
     */
    public void save(RefreshToken token, Duration ttl) {
        String tokenKey = TOKEN_KEY_PREFIX + token.getTokenId();
        String userTokensKey = USER_TOKENS_KEY_PREFIX + token.getUserId();

        // Store token
        redisTemplate.opsForValue().set(tokenKey, token, ttl);

        // Add to user's token set
        redisTemplate.opsForSet().add(userTokensKey, token.getTokenId());
        redisTemplate.expire(userTokensKey, ttl);

        log.debug("Saved refresh token {} for user {}", token.getTokenId(), token.getUserId());
    }

    /**
     * Find a refresh token by ID.
     */
    public Optional<RefreshToken> findById(String tokenId) {
        String key = TOKEN_KEY_PREFIX + tokenId;
        Object value = redisTemplate.opsForValue().get(key);

        if (value instanceof RefreshToken token) {
            return Optional.of(token);
        }
        return Optional.empty();
    }

    /**
     * Delete a refresh token.
     */
    public void deleteById(String tokenId) {
        String key = TOKEN_KEY_PREFIX + tokenId;
        redisTemplate.delete(key);
        log.debug("Deleted refresh token {}", tokenId);
    }

    /**
     * Delete all refresh tokens for a user.
     */
    public void deleteAllByUserId(UUID userId) {
        String userTokensKey = USER_TOKENS_KEY_PREFIX + userId;
        Set<Object> tokenIds = redisTemplate.opsForSet().members(userTokensKey);

        if (tokenIds != null && !tokenIds.isEmpty()) {
            Set<String> keys = tokenIds.stream()
                .map(id -> TOKEN_KEY_PREFIX + id)
                .collect(Collectors.toSet());
            redisTemplate.delete(keys);
            redisTemplate.delete(userTokensKey);
            log.debug("Deleted {} refresh tokens for user {}", tokenIds.size(), userId);
        }
    }

    /**
     * Add token to blacklist (for logout/revocation).
     */
    public void blacklist(String tokenId, Duration ttl) {
        String key = BLACKLIST_KEY_PREFIX + tokenId;
        redisTemplate.opsForValue().set(key, "revoked", ttl);
        log.debug("Blacklisted token {}", tokenId);
    }

    /**
     * Check if token is blacklisted.
     */
    public boolean isBlacklisted(String tokenId) {
        String key = BLACKLIST_KEY_PREFIX + tokenId;
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }
}
