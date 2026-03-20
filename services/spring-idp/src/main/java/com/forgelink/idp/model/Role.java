package com.forgelink.idp.model;

/**
 * RBAC roles for ForgeLink platform.
 */
public enum Role {
    /**
     * Full access - user management, configuration, all data.
     */
    FACTORY_ADMIN,

    /**
     * Read all, write alerts/commands, no user management.
     */
    PLANT_OPERATOR,

    /**
     * Read own area, acknowledge alerts, write device data.
     */
    TECHNICIAN,

    /**
     * Read-only access.
     */
    VIEWER
}
