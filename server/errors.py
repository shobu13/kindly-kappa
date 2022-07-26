from .codes import StatusCode


class RoomNotFoundError(Exception):
    """Custom exception raised when joining a room with an invalid code."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

        self.code = StatusCode.ROOM_NOT_FOUND
        self.message = message
