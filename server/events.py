from __future__ import annotations

from enum import Enum
from typing import Literal, Mapping, TypedDict

from pydantic import BaseModel, validator

from .codes import StatusCode

Position = tuple[int, int]
Replacement = TypedDict("Replacement", {"from": int, "to": int, "value": str})


class EventType(str, Enum):
    """The type of a WebSocket event.

    It is declared as a subclass of str to help serialization.
    """

    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SYNC = "sync"
    MOVE = "move"
    REPLACE = "replace"
    ERROR = "error"


class EventData(BaseModel):
    """The data of a WebSocket event.

    This is just a base class that other classes will inherit from.
    """


class ConnectData(EventData):
    """The data of a connection event.

    Fields:
        connection_type: "create" if the user wants to create the room, "join"
            if the user wants to join the room.
        difficulty (optional): The difficulty of the room, only needed if the
            "connection_type" is "create".
        room_code: The unique four-letters code that will represent the room.
        username: The username of the user creating or joining the room.
    """

    connection_type: Literal["create", "join"]
    difficulty: int | None = None
    room_code: str
    username: str

    @validator("difficulty", pre=True, always=True)
    def valid_difficulty(cls, value, values):  # noqa: U100
        """Validates the difficulty based on the connection type."""
        if values["connection_type"] == "create" and value is None:
            raise ValueError("the difficulty must be specified when creating a room")
        return value


class DisconnectData(EventData):
    """The data of a disconnection event.

    Fields:
        username: The username of the user disconnecting.
    """

    username: str


class SyncData(EventData):
    """The data of a sync event.

    Fields:
        code: The code that already exists in the room.
        collaborators: The list of users that already collaborate in the room.
    """

    code: str
    collaborators: list[str]


class MoveData(EventData):
    """The data of a move event.

    Fields:
        position: The new position of the cursor.
    """

    position: Position


class ReplaceData(EventData):
    """The data of a replace event.

    Fields:
        code: A list of modifications to the code.
    """

    code: list[Replacement]


class ErrorData(EventData):
    """The data of an error event.

    Fields:
        message: The error message.
    """

    message: str


class EventRequest(BaseModel):
    """A WebSocket request event.

    This represent a request made from the client to the server.
    """

    type: EventType  # noqa: VNE003
    data: EventData

    @validator("data", pre=True)
    def valid_data(cls, value: EventData | Mapping, values):  # noqa: U100
        """Validates the data based on the event type."""
        if isinstance(value, EventData):
            value = value.dict()

        match values["type"]:
            case EventType.CONNECT:
                value = ConnectData(**value)
            case EventType.DISCONNECT:
                value = DisconnectData(**value)
            case EventType.SYNC:
                value = SyncData(**value)
            case EventType.REPLACE:
                value = ReplaceData(**value)
            case EventType.ERROR:
                value = ErrorData(**value)
        return value


class EventResponse(EventRequest):
    """A WebSocket event.

    This represents a response sent from the server to the client.
    """

    status_code: StatusCode
