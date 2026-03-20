package com.forgelink.idp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * ForgeLink Identity Provider Application.
 * Provides zero-trust authentication for the steel factory IoT platform.
 */
@SpringBootApplication
public class IdpApplication {

    public static void main(String[] args) {
        SpringApplication.run(IdpApplication.class, args);
    }
}
