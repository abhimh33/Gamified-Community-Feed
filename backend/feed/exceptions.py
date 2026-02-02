"""
Custom Exception Handler for DRF

Provides consistent error response format across the API.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that:
    1. Logs all exceptions
    2. Converts Django exceptions to DRF responses
    3. Provides consistent error format
    """
    
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)
    
    # If DRF handled it, enhance the response
    if response is not None:
        # Ensure consistent format
        if not isinstance(response.data, dict) or 'error' not in response.data:
            response.data = {
                'error': str(exc),
                'details': response.data
            }
        return response
    
    # Handle exceptions that DRF doesn't handle
    if isinstance(exc, IntegrityError):
        logger.warning(f"IntegrityError: {exc}")
        return Response(
            {'error': 'Data integrity error. This may be a duplicate entry.'},
            status=status.HTTP_409_CONFLICT
        )
    
    if isinstance(exc, ValueError):
        return Response(
            {'error': str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Log unexpected exceptions
    logger.exception(f"Unhandled exception: {exc}")
    
    # Return generic error for unexpected exceptions
    return Response(
        {'error': 'An unexpected error occurred.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
