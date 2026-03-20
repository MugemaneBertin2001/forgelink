package com.forgelink.asset;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * ForgeLink Asset Service Application.
 * Manages the ISA-95 asset hierarchy for the steel factory.
 */
@SpringBootApplication
public class AssetServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(AssetServiceApplication.class, args);
    }
}
