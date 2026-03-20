package com.forgelink.idp.config;

import com.forgelink.idp.model.Role;
import com.forgelink.idp.model.User;
import com.forgelink.idp.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.Set;

/**
 * Seeds initial data if configured via environment variables.
 * This is useful for dynamic seeding beyond Flyway migrations.
 */
@Component
@RequiredArgsConstructor
@Slf4j
public class DataSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${seed.admin.email:}")
    private String seedAdminEmail;

    @Value("${seed.admin.password:}")
    private String seedAdminPassword;

    @Value("${seed.admin.plant-id:steel-plant-kigali}")
    private String seedAdminPlantId;

    @Override
    public void run(String... args) {
        if (seedAdminEmail != null && !seedAdminEmail.isEmpty()
                && seedAdminPassword != null && !seedAdminPassword.isEmpty()) {

            if (!userRepository.existsByEmailIgnoreCase(seedAdminEmail)) {
                User admin = User.builder()
                    .email(seedAdminEmail)
                    .passwordHash(passwordEncoder.encode(seedAdminPassword))
                    .firstName("System")
                    .lastName("Administrator")
                    .plantId(seedAdminPlantId)
                    .roles(Set.of(Role.FACTORY_ADMIN))
                    .enabled(true)
                    .locked(false)
                    .build();

                userRepository.save(admin);
                log.info("Created seed admin user: {}", seedAdminEmail);
            } else {
                log.debug("Seed admin user already exists: {}", seedAdminEmail);
            }
        }
    }
}
