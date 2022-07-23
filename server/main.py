"""The main WebSocket server.

This server handles user connection, disconnection and events.
"""
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

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
        """Send JSON data over the WebSocket connection.

        Args:
            data: The data to be sent to the client, it should always contain a
                "type" key to indicate the event type.
        """
        await self._websocket.send_json(data)

    async def receive(self) -> dict:
        """Receive JSON data over the WebSocket connection.

        Returns:
            The data received from the client, it should always contain a "type"
            key to indicate the event type.
        """
        return await self._websocket.receive_json()


class ConnectionManager:
    """Manager for the WebSocket clients."""

    def __init__(self) -> None:
        """Initializes the active connections.

        It stores the active connections and is able to broadcast data.
        """
        self._active_connections: set[Client] = set()

    async def connect(self, client: Client) -> None:
        """Accepts the connection and adds it to the active connections.

        Args:
            client: The Client to which the connection belongs.
        """
        await client.accept()
        self._active_connections.add(client)

    def disconnect(self, client: Client) -> None:
        """Removes the connection from the active connections.

        Args:
            client: The Client to which the connection belongs.
        """
        self._active_connections.remove(client)

    async def send(self, data: dict, client: Client) -> None:
        """Sends data to a given client.

        Args:
            data: The data to be sent to the client, it should always contain a
                "type" key to indicate the event type.
            client: The client that will receive the data.
        """
        await client.send(data)

    async def broadcast(self, data: dict) -> None:
        """Broadcasts data to all active connections.

        Args:
            data: The data to be sent to the clients, it should always contain a
                "type" key to indicate the event type.
        """
        for connection in self._active_connections:
            await connection.send(data)


manager = ConnectionManager()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <input id="input" type="text" autocomplete="off">
        <button onclick="sendMessage(event)">Send</button>
        <ul id="messages"></ul>
        <script>
            let ws = new WebSocket("ws://localhost:8000/ws");

            ws.onmessage = function(event) {
                let data = JSON.parse(event.data);
                switch (data.type) {
                    case "message":
                        let messages = document.getElementById("messages");
                        let message = document.createElement("li");
                        let content = document.createTextNode(data.msg);
                        message.appendChild(content);
                        messages.appendChild(message);
                        break;
                    default:
                        console.log(`Unknown event type '${data.type}'`);
                }
            };

            function sendMessage(event) {
                let input = document.getElementById("input");
                let data = {type: "message", msg: input.value};
                ws.send(JSON.stringify(data));
                input.value = "";
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def chat() -> HTMLResponse:
    """This is the index route for the app.

    Returns:
        The HTML page in which the user can chat.
    """
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """This is the endpoint for the WebSocket connection.

    It creates a client and handles the connection with the ConnectionManager.
    It continuosly receives, sends and broadcasts data to the active clients.
    """
    client = Client(websocket)
    await manager.connect(client)
    await manager.broadcast({"type": "message", "msg": f"{client.id} joined the chat"})

    try:
        while True:
            data = await client.receive()
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(client)
        await manager.broadcast({"type": "message", "msg": f"{client.id} left the chat"})
