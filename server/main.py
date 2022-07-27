"""The main WebSocket server.

This server handles user connection, disconnection and events.
"""
from __future__ import annotations

from dataclasses import dataclass
from json.decoder import JSONDecodeError
from typing import Literal, TypedDict
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic.error_wrappers import ValidationError

from .codes import StatusCode
from .errors import RoomAlreadyExistsError, RoomNotFoundError
from .events import ConnectData, DisconnectData, ErrorData, EventRequest, EventResponse, EventType, ReplaceData

app = FastAPI()


class Client:
    """A WebSocket client."""

    def __init__(self, websocket: WebSocket) -> None:
        """Initializes the WebSocket and the ID.

        A client is identified by an ID and contains the corresponding WebSocket
        that is used to send and receive messages.

        Args:
            websocket: A WebSocket instance.
        """
        self._websocket = websocket
        self.id = uuid4()
        self.default_replacement = EventRequest(
            type=EventType.REPLACE, data=ReplaceData(code=[{"from": 0, "to": 0, "value": ""}])
        )

    async def accept(self) -> None:
        """Accepts the WebSocket connection."""
        await self._websocket.accept()

    async def send(self, data: EventResponse) -> None:
        """Sends JSON data over the WebSocket connection.

        Args:
            data: The data to be sent to the client.
        """
        await self._websocket.send_json(data.dict())

    async def receive(self) -> EventRequest | None:
        """Receives JSON data over the WebSocket connection.

        Returns:
            The data received from the client or None if an error occured.
        """
        try:
            return EventRequest(**await self._websocket.receive_json())
        except (TypeError, JSONDecodeError):
            await self.send(
                EventResponse(
                    type=EventType.ERROR,
                    data=ErrorData(message="Invalid request data."),
                    status_code=StatusCode.INVALID_REQUEST_DATA,
                ),
            )
            return self.default_replacement
        except (KeyError, ValidationError):
            await self.send(
                EventResponse(
                    type=EventType.ERROR,
                    data=ErrorData(message="Data not found."),
                    status_code=StatusCode.DATA_NOT_FOUND,
                ),
            )
            return self.default_replacement
        except (WebSocketDisconnect, RuntimeError):
            return

    async def close(self) -> None:
        """Closes the WebSocket connection."""
        return await self._websocket.close()

    def __eq__(self, other: object) -> bool:
        """Compares the Client to another object.

        If the object is not an instance of Client, NotImplemented is returned.

        Args:
            other: The object to compare the client to.

        Returns:
            True if the id of the client is equal to the other client's id,
            False otherwise.
        """
        if not isinstance(other, Client):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        """Returns the hash value of the Client."""
        return hash(self.id)


@dataclass
class RoomData:
    """A dataclass for data about a specific room."""

    owner_id: UUID
    clients: set[Client]
    code: str


class ActiveRooms(TypedDict):
    """A data structure for active rooms."""

    name: str
    data: RoomData


class ConnectionManager:
    """Manager for the WebSocket clients."""

    def __init__(self) -> None:
        """Initializes the active connections.

        It stores the active connections and is able to broadcast data.
        """
        self._rooms: ActiveRooms = {}

    @staticmethod
    def connect(client: Client, room_code: str, connection_type: Literal["create", "join"]) -> None:
        """Connects the client to a room.

        It creates or joins a room based on the connection_type.

        Args:
            client: The client to connect.
            room_code: The code of the room.
            connection_type: The type of the connection.
        """
        match connection_type:
            case "create":
                manager.create_room(client, room_code)
            case "join":
                manager.join_room(client, room_code)

    def disconnect(self, client: Client, room_code: str) -> None:
        """Removes the connection from the active connections.

        If, after the disconnection, the room is empty, delete it.

        Args:
            client: The client to disconnect.
            room_code: The room from which the client will be disconnected.
        """
        self._rooms[room_code]["clients"].remove(client)

        if len(self._rooms[room_code]["clients"]) == 0:
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


manager = ConnectionManager()


@app.websocket("/room")
async def room(websocket: WebSocket) -> None:
    """This is the endpoint for the WebSocket connection.

    It creates a client and handles connection and disconnection with the
    ConnectionManager. It continuously receives and broadcasts data to the
    active clients.
    """
    client = Client(websocket)
    await client.accept()

    initial_event = await client.receive()
    if initial_event is None:
        return

    if initial_event.type != EventType.CONNECT:
        return

    initial_data: ConnectData = initial_event.data
    room_code = initial_data.room_code

    try:
        ConnectionManager.connect(client, room_code, initial_data.connection_type)
    except (RoomNotFoundError, RoomAlreadyExistsError) as e:
        await client.send(e.data)
        await client.close()
        return

    await manager.broadcast(initial_event, room_code)

    try:
        while True:
            event = await client.receive()
            if event is None:
                return manager.disconnect(client, room_code)

            if event.type == EventType.REPLACE:
                manager.update_code_cache(room_code, event.data)

            await manager.broadcast(event, room_code)
    except WebSocketDisconnect:
        await client.send(
            EventResponse(
                type=EventType.DISCONNECT,
                data=DisconnectData(username=initial_data.username),
                status_code=StatusCode.SUCCESS,
            )
        )
        manager.disconnect(client, room_code)
