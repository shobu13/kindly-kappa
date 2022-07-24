from enum import IntEnum


class KappaCloseCodes(IntEnum):
    """Custom error codes for closing websocket connections."""

    InvalidError = 4000

    RoomNotFound = 4001


class RoomNotFoundError(Exception):
    """Custom exception raised when joining a room with an invalid code."""

    def __init__(self, message: str, code: KappaCloseCodes) -> None:
        super().__init__(message)

        self.code = code.value
        self.message = message
