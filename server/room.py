from uuid import UUID

from server.client import Client
from server.events import Position, ReplaceData
from server.modifiers import Modifiers


class Room:
    """A room handled by the connection manager."""

    def __init__(self, owner_id: UUID, clients: set[Client], difficulty: int) -> None:
        """Initializes the room.

        Args:
            owner_id: The id of the owner of the room.
            clients: The connected clients.
            difficulty: The difficulty of the room.
        """
        self.owner_id = owner_id
        self.clients = clients
        self.difficulty = difficulty
        self.code = ""
        self.cursors: dict[UUID, Position] = {}

    def update_code(self, replace_data: ReplaceData) -> None:
        """Updates the code.

        Args:
            replace_data: A list of changes to make to the code.
        """
        current_code = self.code

        # This checks if there was a de-indent (E.g after a function or class)
        # and adds the newline since it doesn't get passed from the frontend
        if len(replace_data.code) == 2:
            new_value = {"value": "\n    "}
            replace_data.code[1] |= new_value

        for replacement in replace_data.code:
            from_index = replacement["from"]
            to_index = replacement["to"]
            new_value = replacement["value"]

            updated_code = current_code[:from_index] + new_value + current_code[to_index:]
            self.code = updated_code

    def introduce_bugs(self) -> ReplaceData:
        """Introduces bugs based on the current code.

        Returns:
            A list of changes to make to the code.
        """
        current_code = self.code
        modifier = Modifiers(current_code, self.difficulty)

        return modifier.output
