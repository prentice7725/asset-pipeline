class PixelPipelineError(Exception):
    """Base class for errors safe to show directly to a CLI user."""


class ConfigurationError(PixelPipelineError):
    """Invalid or unreadable pipeline configuration."""


class ExternalServiceError(PixelPipelineError):
    """A configured external service failed or could not be reached."""
