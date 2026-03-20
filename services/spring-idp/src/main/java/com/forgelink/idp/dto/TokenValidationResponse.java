package com.forgelink.idp.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Set;

/**
 * Token validation/introspection response DTO.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TokenValidationResponse {

    private boolean active;

    private String sub;

    private String email;

    private Set<String> roles;

    private String plantId;

    private Long exp;

    private Long iat;

    private String iss;
}
