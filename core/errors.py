class InvoiceGeneratorError(Exception):
    """Base class for domain errors raised by services."""


class InvalidInputError(InvoiceGeneratorError):
    """Input or arguments are invalid for the operation."""


class ValidationError(InvoiceGeneratorError):
    """Payload or data validation error."""


class RenderError(InvoiceGeneratorError):
    """PDF rendering failure."""


class FileNotFoundErrorCustom(InvoiceGeneratorError):
    """Expected file is missing."""


class NotFoundError(InvoiceGeneratorError):
    """Requested resource could not be found."""
