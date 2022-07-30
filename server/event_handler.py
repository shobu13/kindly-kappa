from typing import cast

from server.client import Client
from server.codes import StatusCode
from server.connection_manager import ConnectionManager
from server.errors import RoomAlreadyExistsError, RoomNotFoundError
from server.events import (
    ConnectData,
    ErrorData,
    EvaluateData,
    EventRequest,
    EventResponse,
    EventType,
    MoveData,
    ReplaceData,
    SyncData,
)
from server.room import Room
from server.snekbox import evaluate


class EventHandler:
    """An request event handler."""

    def __init__(self, client: Client, manager: ConnectionManager):
        """Initializes the event handler for each client.

        Args:
            client: The client sending the requests.
            manager: The ConnectionManager handling the rooms.
        """
        self.client = client
        self.manager = manager

        # The room code and the room will be set after the initial connection
        # event is handled
        self.room_code: str
        self.room: Room

    async def handle_initial_connection(self, initial_event: EventRequest) -> None:
        """Handles the initial connection event.

        Args:
            initial_event: The initial event sent by the client.
        """
        if initial_event.type != EventType.CONNECT:
            response = EventResponse(
                type=EventType.ERROR,
                data=ErrorData(message="The first event must be of type 'connect'."),
                status_code=StatusCode.INVALID_REQUEST_DATA,
            )
            await self.client.send(response)
            await self.client.close()
            return

        try:
            await self(initial_event)
        except (RoomNotFoundError, RoomAlreadyExistsError) as err:
            await self.client.send(err.response)
            await self.client.close()

    async def __call__(self, request: EventRequest) -> bool:
        """Handle a request received.

        Args:
            request: The data received from the client.

        Returns:
            True if the connection has been closed, False otherwise.

        Raises:
            WebSocketDisconnect: If the event type is a disconnect.
            NotImplementedError: In any other case.
        """
        event_data = request.data

        match request.type:
            case EventType.CONNECT:
                connect_data = cast(ConnectData, event_data)

                self.client.username = connect_data.username
                self.room_code = connect_data.room_code

                match connect_data.connection_type:
                    case "create":
                        if connect_data.difficulty is None:
                            response = EventResponse(
                                type=EventType.ERROR,
                                data=ErrorData(message="Data not found."),
                                status_code=StatusCode.DATA_NOT_FOUND,
                            )
                            await self.client.send(response)
                            return False

                        self.manager.create_room(self.client, connect_data.room_code, connect_data.difficulty)
                        self.room = self.manager._rooms[self.room_code]

                        collaborators = [{"id": c.id.hex, "username": c.username} for c in self.room.clients]

                        # Send a sync event to the client to update the code and
                        # the collaborators' list
                        response = EventResponse(
                            type=EventType.SYNC,
                            data=SyncData(code=self.room.code, collaborators=collaborators),
                            status_code=StatusCode.SUCCESS,
                        )
                        await self.client.send(response)
                    case "join":
                        self.manager.join_room(self.client, self.room_code)
                        self.room = self.manager._rooms[self.room_code]

                        collaborators = [
                            {"id": c.id.hex, "username": c.username}
                            for c in self.room.clients
                            if c.id != self.client.id
                        ]

                        # Send a sync event to the client to update the code and
                        # the collaborators' list
                        response = EventResponse(
                            type=EventType.SYNC,
                            data=SyncData(code=self.room.code, collaborators=collaborators),
                            status_code=StatusCode.SUCCESS,
                        )
                        await self.client.send(response)

                        # Broadcast to other clients a connect event to update
                        # the collaborators' list
                        response = EventResponse(
                            type=EventType.CONNECT,
                            data=connect_data,
                            status_code=StatusCode.SUCCESS,
                        )
                        await self.manager.broadcast(response, self.room_code, sender=self.client)
            case EventType.DISCONNECT:
                collaborators = [
                    {"id": c.id.hex, "username": c.username} for c in self.room.clients if c.id != self.client.id
                ]

                # Broadcast to other clients a sync event to update the
                # collaborators' list
                response = EventResponse(
                    type=EventType.SYNC,
                    data=SyncData(code=self.room.code, collaborators=collaborators),
                    status_code=StatusCode.SUCCESS,
                )
                await self.manager.broadcast(response, self.room_code, sender=self.client)

                self.manager.disconnect(self.client, self.room_code)
                await self.client.close()

                return True
            case EventType.MOVE:
                move_data = cast(MoveData, event_data)
                self.room.cursors[self.client.id] = move_data.position

                # Broadcast to every client a move event to update the cursors'
                # positions
                response = EventResponse(type=EventType.MOVE, data=move_data, status_code=StatusCode.SUCCESS)
                await self.manager.broadcast(response, self.room_code, sender=self.client)
            case EventType.REPLACE:
                replace_data = cast(ReplaceData, event_data)
                self.room.update_code(replace_data)

                # Broadcast to every client a replace event to update the code
                response = EventResponse(type=EventType.REPLACE, data=replace_data, status_code=StatusCode.SUCCESS)
                await self.manager.broadcast(response, self.room_code, sender=self.client)
            case EventType.SEND_BUGS:
                self.room.introduce_bugs()

                collaborators = [{"id": c.id.hex, "username": c.username} for c in self.room.clients]

                # Broadcast to every client a sync event to update the code
                response = EventResponse(
                    type=EventType.SYNC,
                    data=SyncData(code=self.room.code, collaborators=collaborators),
                    status_code=StatusCode.SUCCESS,
                )
                await self.manager.broadcast(response, self.room_code)
            case EventType.EVALUATE:
                result = evaluate(self.room.code)

                # Broadcast to every client an evaluate event to show the result
                response = EventResponse(
                    type=EventType.EVALUATE,
                    data=EvaluateData(result=result),
                    status_code=StatusCode.SUCCESS,
                )
                await self.manager.broadcast(response, self.room_code)
            case _:
                # Anything that doesn't match the request type
                response = EventResponse(
                    type=EventType.ERROR,
                    data=ErrorData(message="This has not been implemented yet."),
                    status_code=StatusCode.INVALID_REQUEST_DATA,
                )
                await self.client.send(response)

        return False
