package com.forgelink.idp.exception;

/**
 * Exception thrown when a locked user attempts to login.
 */
public class UserLockedException extends RuntimeException {

    public UserLockedException(String message) {
        super(message);
    }
}
