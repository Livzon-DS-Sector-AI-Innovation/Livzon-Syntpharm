"""Audit-based OCR failure recorder.

Implements the OCRFailureRecorder protocol to persist OCR failures to the audit log,
providing durable, queryable records for support and debugging.
"""

import logging
import uuid
from typing import Any

from app.core.logging_config import request_id_var
from app.platform.audit.service import record_audit_log

logger = logging.getLogger(__name__)


class AuditFailureRecorder:
    """Records OCR failures to the audit log.

    This recorder writes OCR failures to the audit log with structured context,
    making them queryable by request_id and resource identifiers.
    """

    def __init__(self, db: Any) -> None:
        """Initialize with a database session.

        Args:
            db: SQLAlchemy async session for writing audit logs
        """
        self.db = db

    def record_failure(
        self,
        *,
        input_name: str,
        engine: str,
        output_format: str,
        error_type: str,
        error_message: str,
        request_id: str | None = None,
        module: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        """Record an OCR failure to the audit log.

        This is a synchronous method that schedules an async task to write the audit log.
        The actual write happens asynchronously to avoid blocking the OCR call.

        Args:
            input_name: Name of the input file/image
            engine: OCR engine that failed (pp_ocr or pp_structurev3)
            output_format: Requested output format
            error_type: Type of error (e.g., "OCRError", "TimeoutError")
            error_message: Human-readable error message (truncated to 500 chars)
            request_id: Request correlation ID (from context if not provided)
            module: Module that initiated the OCR call
            resource_type: Type of resource being processed
            resource_id: ID of the resource being processed
        """
        import asyncio

        # Use provided request_id or get from context
        if request_id is None:
            request_id = request_id_var.get()

        # Truncate error message to avoid bloating audit log
        truncated_message = error_message[:500] if len(error_message) > 500 else error_message

        # Build structured extra context
        extra = {
            "ocr_engine": engine,
            "ocr_output_format": output_format,
            "ocr_input": input_name,
            "error_type": error_type,
            "error_message": truncated_message,
        }

        if module:
            extra["module"] = module

        # Parse resource_id as UUID if provided
        resource_uuid = None
        if resource_id:
            try:
                resource_uuid = uuid.UUID(resource_id)
            except (ValueError, AttributeError):
                logger.warning(f"Invalid resource_id format: {resource_id}")

        # Schedule async write
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._write_audit_log(
                    request_id=request_id,
                    resource_type=resource_type or "ocr_document",
                    resource_id=resource_uuid,
                    extra=extra,
                    input_name=input_name,
                    engine=engine,
                )
            )
        except RuntimeError:
            # No running loop - this is a sync context, log warning
            logger.warning(
                "Cannot write OCR failure to audit log: no async loop available",
                extra={
                    "ocr_input": input_name,
                    "ocr_engine": engine,
                },
            )

    async def _write_audit_log(
        self,
        *,
        request_id: str | None,
        resource_type: str,
        resource_id: uuid.UUID | None,
        extra: dict[str, Any],
        input_name: str,
        engine: str,
    ) -> None:
        """Actually write the audit log entry.

        Args:
            request_id: Request correlation ID
            resource_type: Type of resource
            resource_id: UUID of resource
            extra: Extra context data
            input_name: Input file name (for error logging)
            engine: OCR engine name (for error logging)
        """
        try:
            await record_audit_log(
                self.db,
                action="ocr_extraction_failed",
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                extra=extra,
            )
            await self.db.commit()
        except Exception as e:
            # Don't let audit logging failures break the OCR flow
            logger.error(
                "Failed to record OCR failure to audit log",
                extra={
                    "ocr_input": input_name,
                    "ocr_engine": engine,
                    "audit_error": str(e),
                },
                exc_info=True,
            )
