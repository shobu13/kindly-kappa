from typing import Literal, TypeAlias, TypedDict
from uuid import UUID

from server.client import Client
from server.errors import RoomAlreadyExistsError, RoomNotFoundError
from server.events import EventResponse, ReplaceData


class RoomData(TypedDict):
    """A dataclass for data about a specific room."""

    owner_id: UUID
    clients: set[Client]
    code: str


ActiveRooms: TypeAlias = dict[str, RoomData]


class ConnectionManager:
    """Manager for the WebSocket clients."""

    def __init__(self) -> None:
        """Initializes the active connections.

        It stores the active connections and is able to broadcast data.
        """
        self._rooms: ActiveRooms = {}

    def connect(self, client: Client, room_code: str, connection_type: Literal["create", "join"]) -> None:
        """Connects the client to a room.

        It creates or joins a room based on the connection_type.

        Args:
            client: The client to connect.
            room_code: The code of the room.
            connection_type: The type of the connection.
        """
        match connection_type:
            case "create":
                self.create_room(client, room_code)
            case "join":
                self.join_room(client, room_code)

    def disconnect(self, client: Client, room_code: str) -> None:
        """Removes the connection from the active connections.

        If, after the disconnection, the room is empty, delete it.

        Args:
            client: The client to disconnect.
            room_code: The room from which the client will be disconnected.
        """
        self._rooms[room_code]["clients"].remove(client)

        if not self._rooms[room_code]["clients"]:
            del self._rooms[room_code]

    def create_room(self, client: Client, room_code: str) -> None:
        """Create the room for the client.

        Args:
            client: The client that will join to the new room.
            room_code: The room to which the client will be connected.
        """
        if not self._room_exists(room_code):
            self._rooms[room_code] = {"owner_id": client.id, "clients": {client}, "code": ""}
        else:
            raise RoomAlreadyExistsError(f"The room with code '{room_code}' already exists.")

    def join_room(self, client: Client, room_code: str) -> None:
        """Adds a client to an active room.

        Args:
            client: The client that will join the given room.
            room_code: The room to which the client will be connected.
        """
        if self._room_exists(room_code):
            self._rooms[room_code]["clients"].add(client)
        else:
            raise RoomNotFoundError(f"The room with code '{room_code}' was not found.")

    def update_code_cache(self, room_code: str, replace_data: ReplaceData) -> None:
        """Updates the code cache for a particular room.

        Args:
            room_code: The code associated with a particular room.
            code: A list of changes to make to the code cache.
        """
        if self._room_exists(room_code):
            current_code = self._rooms[room_code]["code"]
            for replacement in replace_data.code:
                from_index = replacement["from"]
                to_index = replacement["to"]
                new_value = replacement["value"]

                updated_code = current_code[:from_index] + new_value + current_code[to_index:]
                self._rooms[room_code]["code"] = updated_code

    async def broadcast(self, data: EventResponse, room_code: str, sender: Client | None = None) -> None:
        """Broadcasts data to all active connections.

        Args:
            data: The data to be sent to the clients.
            room_code: The room to which the data will be sent.
            sender (optional): The client who sent the message.
        """
        for connection in self._rooms[room_code]["clients"]:
            if connection == sender:
                continue
            await connection.send(data)

    def _room_exists(self, room_code: str) -> bool:
        """Checks if a room exists.

        Args:
            room_code: The code associated with a particular room.

        Returns:
            True if the room exists. False otherwise.
        """
        if room_code in self._rooms:
            return True
        return False
