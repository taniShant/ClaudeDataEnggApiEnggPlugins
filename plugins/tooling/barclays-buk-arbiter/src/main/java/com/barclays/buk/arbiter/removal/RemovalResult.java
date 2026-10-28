package com.barclays.buk.arbiter.removal;

/**
 * Result object for code removal operations.
 * Serialized to JSON for communication between Java tool and Python.
 */
public class RemovalResult {
    private String status;        // "success", "not_found", "error"
    private String message;       // Human-readable message
    private int removedLines;     // Number of lines removed (0 if not found)
    private String errorDetails;  // Error details if status is "error"

    public RemovalResult(String status, String message, int removedLines, String errorDetails) {
        this.status = status;
        this.message = message;
        this.removedLines = removedLines;
        this.errorDetails = errorDetails;
    }

    public static RemovalResult success(String message, int removedLines) {
        return new RemovalResult("success", message, removedLines, null);
    }

    public static RemovalResult notFound(String message) {
        return new RemovalResult("not_found", message, 0, null);
    }

    public static RemovalResult error(String message, String errorDetails) {
        return new RemovalResult("error", message, 0, errorDetails);
    }

    // Getters for JSON serialization
    public String getStatus() {
        return status;
    }

    public String getMessage() {
        return message;
    }

    public int getRemovedLines() {
        return removedLines;
    }

    public String getErrorDetails() {
        return errorDetails;
    }

    @Override
    public String toString() {
        return "RemovalResult{" +
                "status='" + status + '\'' +
                ", message='" + message + '\'' +
                ", removedLines=" + removedLines +
                ", errorDetails='" + errorDetails + '\'' +
                '}';
    }
}
