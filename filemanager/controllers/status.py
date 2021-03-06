"""Provides the status endpoint for the filemanager service."""

from typing import Tuple, Optional, Any

from http import HTTPStatus as status

from ..services import database
# from ..process import upload as filesystem

Response = Tuple[Optional[dict], status, dict]


def service_status(*args: Any, **kwargs: Any) -> Response:
    """Exercise dependencies and verify operational status."""
    response_data = {}
    response_data['database'] = database.is_available()
    # response_data['filesystem'] = filesystem.is_available()
    if not all(response_data.values()):
        return response_data, status.SERVICE_UNAVAILABLE, {}
    return response_data, status.OK, {}
