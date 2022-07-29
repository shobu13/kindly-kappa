"""The main WebSocket server.

This server handles user connection, disconnection and events.
"""
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from server.client import Client
from server.connection_manager import ConnectionManager
from server.errors import RoomAlreadyExistsError, RoomNotFoundError
from server.events import EventHandler, EventType

app = FastAPI()


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
    handler = EventHandler(client, manager)

    initial_event = await client.receive()
    if initial_event.type != EventType.CONNECT:
        return

    room_code = initial_event.data.room_code

    try:
        await handler(initial_event, room_code)
    except (RoomNotFoundError, RoomAlreadyExistsError) as err:
        await client.send(err.response)
        await client.close()
        return

    try:
        while True:
            event = await client.receive()
            buggy, sender, event_data = await handler(event, room_code)

            await manager.broadcast(event_data, room_code, sender=sender, buggy=buggy)
    except WebSocketDisconnect as err:
        await manager.broadcast(err.response, room_code, sender=client)
        manager.disconnect(client, room_code)
    except NotImplementedError as err:
        await client.send(err.response)
