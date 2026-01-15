"""Domain exceptions for quotation generator."""

from typing import Any, Optional


class QuotationGeneratorError(Exception):
    """Base exception for quotation generator module."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None) -> None:
        """Initialize the exception.

        Args:
            message: Error message.
            details: Additional error details.
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class CSVParsingError(QuotationGeneratorError):
    """Error parsing CSV file."""

    pass


class MissingColumnsError(CSVParsingError):
    """Required columns missing from CSV.

    Attributes:
        missing_columns: List of missing column names.
    """

    def __init__(self, missing_columns: list[str]) -> None:
        """Initialize with missing columns.

        Args:
            missing_columns: List of missing column names.
        """
        self.missing_columns = missing_columns
        message = f"Missing required columns: {', '.join(missing_columns)}"
        super().__init__(message, details={"missing_columns": missing_columns})


class InvalidCSVDataError(CSVParsingError):
    """Invalid data in CSV row.

    Attributes:
        row_index: Index of the invalid row.
        field: Name of the invalid field.
        value: The invalid value.
        expected: Description of expected format.
    """

    def __init__(
        self,
        row_index: int,
        field: str,
        value: Any,
        expected: str,
    ) -> None:
        """Initialize with validation error details.

        Args:
            row_index: Index of the invalid row.
            field: Name of the invalid field.
            value: The invalid value.
            expected: Description of expected format.
        """
        self.row_index = row_index
        self.field = field
        self.value = value
        self.expected = expected
        message = f"Row {row_index}: Invalid value '{value}' for field '{field}'. Expected: {expected}"
        super().__init__(
            message,
            details={
                "row_index": row_index,
                "field": field,
                "value": value,
                "expected": expected,
            },
        )


class ValidationError(QuotationGeneratorError):
    """Business validation error.

    Attributes:
        errors: List of validation errors.
    """

    def __init__(self, errors: list[dict[str, Any]]) -> None:
        """Initialize with validation errors.

        Args:
            errors: List of validation error dictionaries.
        """
        self.errors = errors
        message = f"{len(errors)} validation error(s)"
        super().__init__(message, details={"errors": errors})


class BoondManagerAPIError(QuotationGeneratorError):
    """Error from BoondManager API.

    Attributes:
        status_code: HTTP status code.
        response_body: Response body from API.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        response_body: Optional[str] = None,
    ) -> None:
        """Initialize with API error details.

        Args:
            status_code: HTTP status code.
            message: Error message.
            response_body: Raw response body.
        """
        self.status_code = status_code
        self.response_body = response_body
        full_message = f"BoondManager API error ({status_code}): {message}"
        super().__init__(
            full_message,
            details={
                "status_code": status_code,
                "response_body": response_body,
            },
        )


class TemplateNotFoundError(QuotationGeneratorError):
    """No active template found."""

    def __init__(self) -> None:
        """Initialize template not found error."""
        super().__init__(
            "No active quotation template found. Please upload a template first.",
            details={"error_code": "TEMPLATE_NOT_FOUND"},
        )


class PDFConversionError(QuotationGeneratorError):
    """Error converting Excel to PDF.

    Attributes:
        filename: Name of the file that failed to convert.
        stderr: Error output from conversion process.
    """

    def __init__(
        self,
        filename: str,
        stderr: Optional[str] = None,
    ) -> None:
        """Initialize with conversion error details.

        Args:
            filename: Name of the file that failed.
            stderr: Standard error output.
        """
        self.filename = filename
        self.stderr = stderr
        message = f"Failed to convert '{filename}' to PDF"
        if stderr:
            message += f": {stderr[:200]}"
        super().__init__(
            message,
            details={"filename": filename, "stderr": stderr},
        )


class PDFMergeError(QuotationGeneratorError):
    """Error merging PDF files."""

    def __init__(self, message: str = "Failed to merge PDF files") -> None:
        """Initialize merge error.

        Args:
            message: Error message.
        """
        super().__init__(message)


class BatchNotFoundError(QuotationGeneratorError):
    """Batch not found.

    Attributes:
        batch_id: The batch ID that was not found.
    """

    def __init__(self, batch_id: str) -> None:
        """Initialize with batch ID.

        Args:
            batch_id: The missing batch ID.
        """
        self.batch_id = batch_id
        super().__init__(
            f"Batch '{batch_id}' not found",
            details={"batch_id": batch_id},
        )


class BatchExpiredError(QuotationGeneratorError):
    """Batch has expired.

    Attributes:
        batch_id: The expired batch ID.
    """

    def __init__(self, batch_id: str) -> None:
        """Initialize with batch ID.

        Args:
            batch_id: The expired batch ID.
        """
        self.batch_id = batch_id
        super().__init__(
            f"Batch '{batch_id}' has expired. Please upload CSV again.",
            details={"batch_id": batch_id},
        )


class QuotationGenerationError(QuotationGeneratorError):
    """Error generating a single quotation.

    Attributes:
        resource_trigramme: Trigramme of the resource.
        step: Step where the error occurred.
    """

    def __init__(
        self,
        resource_trigramme: str,
        step: str,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize with generation error details.

        Args:
            resource_trigramme: Trigramme of the resource.
            step: Step where error occurred.
            original_error: The underlying exception.
        """
        self.resource_trigramme = resource_trigramme
        self.step = step
        self.original_error = original_error
        message = f"Failed to generate quotation for {resource_trigramme} at step '{step}'"
        if original_error:
            message += f": {str(original_error)}"
        super().__init__(
            message,
            details={
                "resource_trigramme": resource_trigramme,
                "step": step,
                "original_error": str(original_error) if original_error else None,
            },
        )


class DownloadNotReadyError(QuotationGeneratorError):
    """Batch download is not ready yet.

    Attributes:
        batch_id: The batch ID.
        reason: Reason why download is not ready.
    """

    def __init__(self, message: str, batch_id: Optional[str] = None) -> None:
        """Initialize download not ready error.

        Args:
            message: Error message.
            batch_id: Optional batch ID.
        """
        self.batch_id = batch_id
        super().__init__(message, details={"batch_id": batch_id})


class TemplateStorageError(QuotationGeneratorError):
    """Error storing or retrieving template."""

    pass


class TemplateFillerError(QuotationGeneratorError):
    """Error filling template with data."""

    pass
