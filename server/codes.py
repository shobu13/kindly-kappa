from enum import IntEnum


class StatusCode(IntEnum):
    """Custom status codes for a WebSocket event."""

    SUCCESS = 4000
    ROOM_NOT_FOUND = 4001
