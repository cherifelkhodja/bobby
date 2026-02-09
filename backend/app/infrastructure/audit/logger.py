"""Structured audit logging for security-sensitive operations."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

import structlog


class AuditAction(str, Enum):
    """Audit action types."""

    # Authentication
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_SUCCESS = "password_reset_success"
    TOKEN_REFRESH = "token_refresh"

    # User management
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_ACTIVATE = "user_activate"
    USER_DEACTIVATE = "user_deactivate"
    ROLE_CHANGE = "role_change"

    # Invitations
    INVITATION_CREATE = "invitation_create"
    INVITATION_ACCEPT = "invitation_accept"
    INVITATION_DELETE = "invitation_delete"

    # Cooptations
    COOPTATION_CREATE = "cooptation_create"
    COOPTATION_UPDATE = "cooptation_update"
    COOPTATION_STATUS_CHANGE = "cooptation_status_change"

    # CV Transformer
    CV_TRANSFORM = "cv_transform"
    CV_TEMPLATE_UPLOAD = "cv_template_upload"

    # HR / Job postings
    JOB_POSTING_CREATE = "job_posting_create"
    JOB_POSTING_PUBLISH = "job_posting_publish"
    JOB_POSTING_CLOSE = "job_posting_close"
    APPLICATION_STATUS_CHANGE = "application_status_change"
    APPLICATION_VIEW_CV = "application_view_cv"

    # Admin
    ADMIN_ACCESS = "admin_access"
    BOOND_SYNC = "boond_sync"

    # Security events
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class AuditResource(str, Enum):
    """Audit resource types."""

    USER = "user"
    INVITATION = "invitation"
    COOPTATION = "cooptation"
    OPPORTUNITY = "opportunity"
    CV = "cv"
    TEMPLATE = "template"
    JOB_POSTING = "job_posting"
    APPLICATION = "application"
    SESSION = "session"
    SYSTEM = "system"


class AuditLogger:
    """Structured audit logger for security events."""

    def __init__(self) -> None:
        """Initialize audit logger with structlog."""
        self.logger = structlog.get_logger("audit")

    def log(
        self,
        action: AuditAction,
        resource: AuditResource,
        *,
        user_id: UUID | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            action: The action being performed
            resource: The type of resource being acted upon
            user_id: ID of the user performing the action
            resource_id: ID of the resource being acted upon
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional details about the action
            success: Whether the action succeeded
            error_message: Error message if action failed
        """
        event_data = {
            "action": action.value,
            "resource": resource.value,
            "timestamp": datetime.now(UTC).isoformat(),
            "success": success,
        }

        if user_id:
            event_data["user_id"] = str(user_id)
        if resource_id:
            event_data["resource_id"] = str(resource_id)
        if ip_address:
            event_data["ip_address"] = ip_address
        if user_agent:
            event_data["user_agent"] = user_agent[:200]  # Truncate long user agents
        if details:
            event_data["details"] = details
        if error_message:
            event_data["error"] = error_message

        # Log at appropriate level
        if success:
            self.logger.info("audit_event", **event_data)
        else:
            self.logger.warning("audit_event", **event_data)

    # Convenience methods for common operations

    def log_login_success(
        self,
        user_id: UUID,
        email: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log successful login."""
        self.log(
            AuditAction.LOGIN_SUCCESS,
            AuditResource.SESSION,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email},
        )

    def log_login_failure(
        self,
        email: str,
        reason: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Log failed login attempt."""
        self.log(
            AuditAction.LOGIN_FAILURE,
            AuditResource.SESSION,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"email": email},
            success=False,
            error_message=reason,
        )

    def log_role_change(
        self,
        admin_id: UUID,
        target_user_id: UUID,
        old_role: str,
        new_role: str,
        ip_address: str | None = None,
    ) -> None:
        """Log role change event."""
        self.log(
            AuditAction.ROLE_CHANGE,
            AuditResource.USER,
            user_id=admin_id,
            resource_id=str(target_user_id),
            ip_address=ip_address,
            details={"old_role": old_role, "new_role": new_role},
        )

    def log_user_delete(
        self,
        admin_id: UUID,
        deleted_user_id: UUID,
        deleted_email: str,
        ip_address: str | None = None,
    ) -> None:
        """Log user deletion event."""
        self.log(
            AuditAction.USER_DELETE,
            AuditResource.USER,
            user_id=admin_id,
            resource_id=str(deleted_user_id),
            ip_address=ip_address,
            details={"deleted_email": deleted_email},
        )

    def log_cv_transform(
        self,
        user_id: UUID,
        filename: str,
        template: str,
        success: bool,
        ip_address: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Log CV transformation event."""
        self.log(
            AuditAction.CV_TRANSFORM,
            AuditResource.CV,
            user_id=user_id,
            ip_address=ip_address,
            details={"filename": filename, "template": template},
            success=success,
            error_message=error_message,
        )

    def log_rate_limit_exceeded(
        self,
        endpoint: str,
        ip_address: str | None = None,
        user_id: UUID | None = None,
    ) -> None:
        """Log rate limit exceeded event."""
        self.log(
            AuditAction.RATE_LIMIT_EXCEEDED,
            AuditResource.SYSTEM,
            user_id=user_id,
            ip_address=ip_address,
            details={"endpoint": endpoint},
            success=False,
            error_message="Rate limit exceeded",
        )

    def log_unauthorized_access(
        self,
        endpoint: str,
        required_role: str | None = None,
        user_role: str | None = None,
        ip_address: str | None = None,
        user_id: UUID | None = None,
    ) -> None:
        """Log unauthorized access attempt."""
        self.log(
            AuditAction.UNAUTHORIZED_ACCESS,
            AuditResource.SYSTEM,
            user_id=user_id,
            ip_address=ip_address,
            details={
                "endpoint": endpoint,
                "required_role": required_role,
                "user_role": user_role,
            },
            success=False,
            error_message="Unauthorized access attempt",
        )


# Global audit logger instance
audit_logger = AuditLogger()
