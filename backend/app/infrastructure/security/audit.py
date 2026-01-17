"""
Audit logging infrastructure.

Provides secure audit logging for sensitive actions.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
from uuid import UUID, uuid4

from app.infrastructure.observability.logging import get_logger

logger = get_logger("audit")


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGE = "auth.password.change"
    PASSWORD_RESET_REQUEST = "auth.password.reset_request"
    PASSWORD_RESET_COMPLETE = "auth.password.reset_complete"
    TOKEN_REFRESH = "auth.token.refresh"

    # User management events
    USER_CREATE = "user.create"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ACTIVATE = "user.activate"
    USER_DEACTIVATE = "user.deactivate"
    USER_ROLE_CHANGE = "user.role.change"

    # Invitation events
    INVITATION_CREATE = "invitation.create"
    INVITATION_ACCEPT = "invitation.accept"
    INVITATION_DELETE = "invitation.delete"
    INVITATION_RESEND = "invitation.resend"

    # Cooptation events
    COOPTATION_CREATE = "cooptation.create"
    COOPTATION_STATUS_CHANGE = "cooptation.status.change"
    COOPTATION_DELETE = "cooptation.delete"

    # Opportunity events
    OPPORTUNITY_PUBLISH = "opportunity.publish"
    OPPORTUNITY_CLOSE = "opportunity.close"

    # Admin actions
    ADMIN_BOOND_SYNC = "admin.boond.sync"
    ADMIN_TEMPLATE_UPLOAD = "admin.template.upload"
    ADMIN_DATA_EXPORT = "admin.data.export"

    # Security events
    RATE_LIMIT_EXCEEDED = "security.rate_limit.exceeded"
    INVALID_TOKEN = "security.token.invalid"
    PERMISSION_DENIED = "security.permission.denied"


@dataclass
class AuditEvent:
    """
    Audit event record.

    Contains all information about an auditable action.
    """

    id: UUID = field(default_factory=uuid4)
    event_type: AuditEventType = AuditEventType.LOGIN_SUCCESS
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "id": str(self.id),
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "user_id": self.user_id,
            "user_email": self.user_email,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "details": self.details,
            "success": self.success,
            "error_message": self.error_message,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class AuditLogger:
    """
    Audit logger for recording sensitive actions.

    Logs audit events to structured logging and optionally
    to a persistent store (database, external service).

    Example:
        audit = AuditLogger()

        audit.log(
            AuditEventType.LOGIN_SUCCESS,
            user_id="123",
            user_email="user@example.com",
            ip_address="192.168.1.1",
        )
    """

    def __init__(
        self,
        persist_func: Optional[Callable[[AuditEvent], None]] = None,
    ):
        """
        Initialize the audit logger.

        Args:
            persist_func: Optional function to persist events to storage
        """
        self._persist = persist_func

    def log(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of audit event
            user_id: ID of the user performing the action
            user_email: Email of the user
            ip_address: Client IP address
            user_agent: Client user agent
            resource_type: Type of resource being acted upon
            resource_id: ID of the resource
            action: Description of the action
            details: Additional details
            success: Whether the action was successful
            error_message: Error message if failed

        Returns:
            The created AuditEvent
        """
        event = AuditEvent(
            event_type=event_type,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
            success=success,
            error_message=error_message,
        )

        # Log to structured logging
        log_method = logger.info if success else logger.warning
        log_method(
            f"Audit: {event_type.value}",
            audit_event_id=str(event.id),
            audit_event_type=event_type.value,
            audit_user_id=user_id,
            audit_user_email=user_email,
            audit_ip=ip_address,
            audit_resource=f"{resource_type}:{resource_id}" if resource_type else None,
            audit_success=success,
            audit_error=error_message,
        )

        # Persist if configured
        if self._persist:
            try:
                self._persist(event)
            except Exception as e:
                logger.error(
                    "Failed to persist audit event",
                    audit_event_id=str(event.id),
                    error=str(e),
                )

        return event

    def log_auth_success(
        self,
        user_id: str,
        user_email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """Log a successful authentication."""
        return self.log(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            action="User logged in successfully",
        )

    def log_auth_failure(
        self,
        email: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """Log a failed authentication attempt."""
        return self.log(
            AuditEventType.LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            action="Login attempt failed",
            success=False,
            error_message=reason,
        )

    def log_resource_change(
        self,
        event_type: AuditEventType,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEvent:
        """Log a resource change event."""
        return self.log(
            event_type,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
        )


# Global audit logger instance
audit_log = AuditLogger()
