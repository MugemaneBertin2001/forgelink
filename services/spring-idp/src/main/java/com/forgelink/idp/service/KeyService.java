package com.forgelink.idp.service;

import com.forgelink.idp.config.JwtConfig;
import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.KeyFactory;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;

/**
 * Service for managing RSA key pairs used for JWT signing.
 */
@Service
@RequiredArgsConstructor
@Slf4j
public class KeyService {

    private final JwtConfig jwtConfig;

    private RSAPrivateKey privateKey;
    private RSAPublicKey publicKey;

    @PostConstruct
    public void init() {
        try {
            loadOrGenerateKeys();
        } catch (Exception e) {
            log.error("Failed to initialize keys", e);
            throw new RuntimeException("Failed to initialize JWT keys", e);
        }
    }

    /**
     * Get the RSA private key for signing.
     */
    public RSAPrivateKey getPrivateKey() {
        return privateKey;
    }

    /**
     * Get the RSA public key for verification.
     */
    public RSAPublicKey getPublicKey() {
        return publicKey;
    }

    /**
     * Get the key ID for JWKS.
     */
    public String getKeyId() {
        return jwtConfig.getKeyId();
    }

    private void loadOrGenerateKeys() throws Exception {
        Path privateKeyPath = Path.of(jwtConfig.getPrivateKeyPath());
        Path publicKeyPath = Path.of(jwtConfig.getPublicKeyPath());

        if (Files.exists(privateKeyPath) && Files.exists(publicKeyPath)) {
            log.info("Loading existing RSA key pair from disk");
            loadKeysFromFiles(privateKeyPath, publicKeyPath);
        } else {
            log.warn("RSA key files not found, generating new key pair");
            generateAndSaveKeys(privateKeyPath, publicKeyPath);
        }

        log.info("RSA key pair initialized successfully");
    }

    private void loadKeysFromFiles(Path privateKeyPath, Path publicKeyPath) throws Exception {
        // Load private key
        String privateKeyPem = Files.readString(privateKeyPath);
        privateKey = loadPrivateKey(privateKeyPem);

        // Load public key
        String publicKeyPem = Files.readString(publicKeyPath);
        publicKey = loadPublicKey(publicKeyPem);
    }

    private RSAPrivateKey loadPrivateKey(String pem) throws Exception {
        String privateKeyPEM = pem
            .replace("-----BEGIN PRIVATE KEY-----", "")
            .replace("-----BEGIN RSA PRIVATE KEY-----", "")
            .replace("-----END PRIVATE KEY-----", "")
            .replace("-----END RSA PRIVATE KEY-----", "")
            .replaceAll("\\s", "");

        byte[] encoded = Base64.getDecoder().decode(privateKeyPEM);
        KeyFactory keyFactory = KeyFactory.getInstance("RSA");
        PKCS8EncodedKeySpec keySpec = new PKCS8EncodedKeySpec(encoded);
        return (RSAPrivateKey) keyFactory.generatePrivate(keySpec);
    }

    private RSAPublicKey loadPublicKey(String pem) throws Exception {
        String publicKeyPEM = pem
            .replace("-----BEGIN PUBLIC KEY-----", "")
            .replace("-----END PUBLIC KEY-----", "")
            .replaceAll("\\s", "");

        byte[] encoded = Base64.getDecoder().decode(publicKeyPEM);
        KeyFactory keyFactory = KeyFactory.getInstance("RSA");
        X509EncodedKeySpec keySpec = new X509EncodedKeySpec(encoded);
        return (RSAPublicKey) keyFactory.generatePublic(keySpec);
    }

    private void generateAndSaveKeys(Path privateKeyPath, Path publicKeyPath) throws Exception {
        // Generate key pair
        KeyPairGenerator keyGen = KeyPairGenerator.getInstance("RSA");
        keyGen.initialize(2048);
        KeyPair keyPair = keyGen.generateKeyPair();

        privateKey = (RSAPrivateKey) keyPair.getPrivate();
        publicKey = (RSAPublicKey) keyPair.getPublic();

        // Save to files
        try {
            Files.createDirectories(privateKeyPath.getParent());

            String privateKeyPem = "-----BEGIN PRIVATE KEY-----\n" +
                Base64.getMimeEncoder(64, "\n".getBytes()).encodeToString(privateKey.getEncoded()) +
                "\n-----END PRIVATE KEY-----\n";
            Files.writeString(privateKeyPath, privateKeyPem);

            String publicKeyPem = "-----BEGIN PUBLIC KEY-----\n" +
                Base64.getMimeEncoder(64, "\n".getBytes()).encodeToString(publicKey.getEncoded()) +
                "\n-----END PUBLIC KEY-----\n";
            Files.writeString(publicKeyPath, publicKeyPem);

            log.info("Generated and saved new RSA key pair");
        } catch (IOException e) {
            log.warn("Could not save keys to disk (running in container?): {}", e.getMessage());
        }
    }
}
