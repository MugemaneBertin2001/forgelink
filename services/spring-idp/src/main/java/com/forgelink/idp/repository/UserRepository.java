package com.forgelink.idp.repository;

import com.forgelink.idp.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.Optional;
import java.util.UUID;

/**
 * Repository for User entity.
 */
@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    /**
     * Find user by email (case-insensitive).
     */
    Optional<User> findByEmailIgnoreCase(String email);

    /**
     * Check if email exists.
     */
    boolean existsByEmailIgnoreCase(String email);

    /**
     * Update last login timestamp and IP.
     */
    @Modifying
    @Query("UPDATE User u SET u.lastLoginAt = :timestamp, u.lastLoginIp = :ip, u.failedLoginAttempts = 0 WHERE u.id = :userId")
    void updateLastLogin(@Param("userId") UUID userId, @Param("timestamp") Instant timestamp, @Param("ip") String ip);

    /**
     * Increment failed login attempts.
     */
    @Modifying
    @Query("UPDATE User u SET u.failedLoginAttempts = u.failedLoginAttempts + 1 WHERE u.id = :userId")
    void incrementFailedAttempts(@Param("userId") UUID userId);

    /**
     * Lock user account.
     */
    @Modifying
    @Query("UPDATE User u SET u.locked = true, u.lockedUntil = :until WHERE u.id = :userId")
    void lockUser(@Param("userId") UUID userId, @Param("until") Instant until);

    /**
     * Unlock user account.
     */
    @Modifying
    @Query("UPDATE User u SET u.locked = false, u.lockedUntil = null, u.failedLoginAttempts = 0 WHERE u.id = :userId")
    void unlockUser(@Param("userId") UUID userId);
}
