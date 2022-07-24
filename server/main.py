"""The main WebSocket server.

This server handles user connection, disconnection and events.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict
from uuid import UUID, uuid4

from errors import KappaCloseCodes, RoomNotFoundError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

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

    async def accept(self) -> None:
        """Accepts the WebSocket connection."""
        await self._websocket.accept()

    async def send(self, data: dict) -> None:
        """Sends JSON data over the WebSocket connection.

        Args:
            data: The data to be sent to the client, it should always contain a
                "type" key to indicate the event type.
        """
        await self._websocket.send_json(data)

    async def receive(self) -> dict:
        """Receives JSON data over the WebSocket connection.

        Returns:
            The data received from the client, it should always contain a "type"
            key to indicate the event type.
        """
        return await self._websocket.receive_json()

    async def close(self) -> None:
        """Closes the WebSocket connection."""
        return await self._websocket.close()

    def __eq__(self, other: object) -> bool:
        """Compares the Client to another object.

        If the object is not an instance of Client, NotImplemented is returned.

        Args:
            other: The object to compare the Client to.

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

    def create_room(self, client: Client, room_code: str) -> None:
        """Create the room for the client.

        Args:
            client: The Client to which the connection belongs.
            room_code: The room to which the client will be connected.
        """
        if not self.room_exists(room_code):
            self._rooms[room_code] = {"owner_id": client.id, "clients": set()}
        self._rooms[room_code]["clients"].add(client)

    def join_room(self, client: Client, room_code: str) -> None:
        """Adds a client to an active room.

        Args:
            client: The Client to which the connection belongs.
            room_code: The room from which the client will be disconnected.
        """
        if self.room_exists(room_code):
            self._rooms[room_code]["clients"].add(client)
        else:
            raise RoomNotFoundError(f"The room with code '{room_code}' was not found.", KappaCloseCodes.RoomNotFound)

    def disconnect(self, client: Client, room_code: str) -> None:
        """Removes the connection from the active connections.

        If, after the disconnection, the room is empty, delete it.

        Args:
            client: The Client to which the connection belongs.
            room_code: The room from which the client will be disconnected.
        """
        self._rooms[room_code]["clients"].remove(client)

        if len(self._rooms[room_code]["clients"]) == 0:
            del self._rooms[room_code]

    async def broadcast(self, data: dict, room_code: str, sender: Client | None = None) -> None:
        """Broadcasts data to all active connections.

        Args:
            data: The data to be sent to the clients, it should always contain a
                "type" key to indicate the event type.
            room_code: The room to which the data will be sent.
            sender (optional): The client who sent the message.
        """
        for connection in self._rooms[room_code]["clients"]:
            if connection == sender:
                continue
            await connection.send(data)

    def room_exists(self, room_code: str) -> bool:
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


class ConnectionEventData(BaseModel):
    """A model representing the connection event data."""

    message: str
    difficulty: int
    room_code: str
    connection_type: Literal["create", "join"]


class ConnectionData(BaseModel):
    """A model representing the initial connection."""

    type: str
    data: ConnectionEventData


@app.websocket("/room")
async def room(websocket: WebSocket) -> None:
    """This is the endpoint for the WebSocket connection.

    It creates a client and handles connection and disconnection with the
    ConnectionManager. It continuously receives and broadcasts data to the
    active clients.
    """
    client = Client(websocket)
    await client.accept()
    try:
        initial_data = ConnectionData(**await client.receive())
    except WebSocketDisconnect:
        return

    room_code = initial_data.data.room_code
    if initial_data.type == "connect":
        match initial_data.data.connection_type:
            case "create":
                manager.create_room(client, room_code)
            case "join":
                try:
                    manager.join_room(client, room_code)
                except RoomNotFoundError as e:
                    # Send off to frontend to handle
                    await client.send(
                        {
                            "type": "error",
                            "data": {
                                "message": e.message,
                            },
                            "status_code": KappaCloseCodes.RoomNotFound,
                        }
                    )
                    await client.close()
                    return
            case _:
                raise NotImplementedError

    try:
        while True:
            data = await client.receive()
            await manager.broadcast(data, room_code, sender=client)
    except WebSocketDisconnect:
        manager.disconnect(client, room_code)
