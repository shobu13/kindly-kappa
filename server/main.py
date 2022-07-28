"""The main WebSocket server.

This server handles user connection, disconnection and events.
"""
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from server.client import Client
from server.codes import StatusCode
from server.connection_manager import ConnectionManager
from server.errors import RoomAlreadyExistsError, RoomNotFoundError
from server.events import ConnectData, DisconnectData, EventResponse, EventType

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

    initial_event = await client.receive()
    if initial_event is None:
        return

    if initial_event.type != EventType.CONNECT:
        return

    initial_data: ConnectData = initial_event.data
    room_code = initial_data.room_code

    try:
        manager.connect(client, room_code, initial_data.connection_type)
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
