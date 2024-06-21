"""Interface for interacting with Anki."""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from functools import cached_property
from typing import Any

from markdown import markdown


class DuplicateNoteError(Exception):
    pass


class AnkiConnector:
    def __init__(self):
        self.deck_names = self.invoke("deckNames", {})
        self.media_files = self.invoke("getMediaFilesNames", {})

    """Interface for interacting with Anki."""

    IMAGE_REGEX = r"!\[.*?\]\((.*?)\)"

    def request(self, action: str, **params: Any) -> dict[str, Any]:
        """Constructs a request dictionary with the given action, parameters, and version.

        Args:
            action: The action to be included in the request.
            params: Additional keyword arguments to be included in the request parameters.

        Returns:
            The constructed request dictionary.
        """
        return {"action": action, "params": params, "version": 6}

    def invoke(self, action: str, params: Any) -> Any:
        """Sends a request and returns the result.

        Args:
            action: The action to be included in the request.
            params: Additional arguments to be included in the request parameters.

        Returns:
            Any: The result from the response.

        Raises:
            ValueError: If the response is not valid.
            URLError: If the request fails.
        """
        request_json = json.dumps(self.request(action, **params)).encode("utf-8")
        response = json.load(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8765", request_json)))
        if len(response) != 2:
            error_message = "response has an unexpected number of fields"
        elif "error" not in response:
            error_message = "response is missing required error field"
        elif "result" not in response:
            error_message = "response is missing required result field"
        elif response["error"] is not None:
            error_message = response["error"]
        else:
            return response["result"]

        # Special error cases
        if error_message == "cannot create note because it is a duplicate":
            raise DuplicateNoteError

        # General error case
        raise ValueError(error_message)

    def manki_notes(self) -> list[int]:
        """Fetches the notes tagged with 'mankey' from Anki.

        Returns:
            A list of note IDs.
        """
        params = {"query": "tag:mankey"}
        return self.invoke("findNotes", params)

    def delete_notes(self, notes: list[int]) -> None:
        """Deletes the specified notes from Anki.

        Args:
            notes: A list of note IDs to delete.
        """
        params = {"notes": notes}
        self.invoke("deleteNotes", params)

    def model_names(self) -> list[str]:
        """Fetches the model names from Anki.

        Returns:
            A list of model names.
        """
        return self.invoke("modelNames", {})

    def create_deck(self, deck_name: str) -> None:
        """Creates a deck  if it does not exist."""
        if deck_name not in self.deck_names:
            params = {"deck": deck_name}
            self.deck_names.append(deck_name)
            self.invoke("createDeck", params)

    def store_media_file(self, file_name: str, data: bytes) -> None:
        """Stores a media file.

        Args:
            file_name: The name of the file to be stored.
            data: The data of the file to be stored.

        Returns:
            None
        """
        if file_name not in self.media_files:
            params = {
                "filename": file_name,
                "data": base64.b64encode(data).decode("utf-8"),
            }
            self.media_files.append(file_name)
            self.invoke("storeMediaFile", params)

    def add_flashcard(self, deck_name: str, question: str, answer: str, card_model: str) -> int:
        """Adds a new flashcard.

        Args:
            deck_name: The name of the deck to add the flashcard to.
            question: The question of the flashcard.
            answer: The answer of the flashcard.
            card_model: The model name of the flashcard.

        Returns:
            The result of the request.
        """
        params = {
            "note": {
                "deckName": deck_name,
                "modelName": card_model,
                "fields": {
                    "Front": question,
                    "Back": answer,
                },
                # "options": {"allowDuplicate": True},
                "tags": ["mankey"],
            },
        }
        return self.invoke("addNote", params)

    def update_flashcard(self, deck_name: str, question: str, answer: str, card_model: str, anki_id: int) -> int:
        """Updates an existing flashcard.

        Args:
            question: The new question of the flashcard.
            answer: The new answer of the flashcard.
            card_model: The model name of the flashcard.
            anki_id: The Anki ID of the flashcard to be updated.

        Returns:
            The result of the request.
        """
        params = {
            "note": {
                "deckName": deck_name,
                "id": anki_id,
                "modelName": card_model,
                "fields": {
                    "Front": question,
                    "Back": answer,
                },
                "tags": ["mankey"],
            },
        }
        return self.invoke("updateNote", params)

    def import_flashcard(
        self, deck_name: str, question: str, answer: str, card_model: str, anki_id: int | None
    ) -> int | None:
        """Imports a flashcard.

        Args:
            question: The question of the flashcard.
            answer: The answer of the flashcard.
            card_model: The model name of the flashcard.

        Returns:
            None
        """
        question = self.markdown_to_anki(question)
        answer = self.markdown_to_anki(answer)
        if anki_id:
            params = {"notes": [anki_id]}
            result = self.invoke("notesInfo", params)
            if result == [{}]:
                return self.add_flashcard(deck_name, question, answer, card_model)
            else:
                self.update_flashcard(deck_name, question, answer, card_model, anki_id)
        else:
            return self.add_flashcard(deck_name, question, answer, card_model)

    def import_definition(self, deck_name: str, word: str, definition: str, anki_id: int | None) -> int | None:
        params: dict[str, Any] = {
            "note": {
                "deckName": deck_name,
                "modelName": "Basic (and reversed card)",
                "fields": {
                    "Front": word,
                    "Back": definition,
                },
                "tags": ["mankey"],
            },
        }
        if anki_id:
            params["note"]["id"] = anki_id
            self.invoke("updateNote", params)
            return anki_id
        try:
            return self.invoke("addNote", params)
        except DuplicateNoteError:
            return self.find_definition(word)

    def find_definition(self, word: str) -> int:
        """Finds the Anki ID of a card based on the question.

        Args:
            definition: The definition of the card.

        Returns:
            The Anki ID of the card.
        """
        params = {"query": word}
        matches = self.invoke("findNotes", params)
        if len(matches) == 1:
            return matches[0]

        error_msg = f"Expected 1 match, got {len(matches)}"
        raise ValueError(error_msg)

    def import_question_answer(self, deck_name: str, question: str, answer: str, anki_id: int | None) -> int | None:
        params: dict[str, Any] = {
            "note": {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {
                    "Front": question,
                    "Back": answer,
                },
                "tags": ["mankey"],
            },
        }
        if anki_id:
            params["note"]["id"] = anki_id
            self.invoke("updateNote", params)
            return anki_id
        try:
            return self.invoke("addNote", params)
        except DuplicateNoteError:
            return self.find_question_answer(question)

    def find_question_answer(self, question: str) -> int:
        """Finds the Anki ID of a card based on the question.

        Args:
            definition: The definition of the card.

        Returns:
            The Anki ID of the card.
        """
        params = {"query": question}
        print(question)
        matches = self.invoke("findNotes", params)
        if len(matches) == 1:
            return matches[0]

        error_msg = f"Expected 1 match, got {len(matches)}"
        raise ValueError(error_msg)

    def import_clozure(self, deck_name: str, clozure: str, anki_id: int | None) -> int | None:
        params: dict[str, Any] = {
            "note": {
                "deckName": deck_name,
                "modelName": "Cloze",
                "fields": {
                    "Text": clozure,
                },
                "tags": ["mankey"],
            },
        }
        if anki_id:
            params["note"]["id"] = anki_id
            self.invoke("updateNote", params)
            return anki_id
        try:
            return self.invoke("addNote", params)
        except DuplicateNoteError:
            return self.find_clozure(clozure)

    def find_clozure(self, clozure: str) -> int:
        """Finds the Anki ID of a card based on the question.

        Args:
            clozure: The clozure of the card.

        Returns:
            The Anki ID of the card.
        """
        # Convert closure back to a searchable string
        clozure = re.sub(r"{{c\d::(.*?)}}", r"\1", clozure)

        # Need to escape slashes
        clozure = clozure.replace("\\", "\\\\")

        params = {"query": clozure}
        matches = self.invoke("findNotes", params)
        if len(matches) == 1:
            return matches[0]

        error_msg = f"Expected 1 match, got {len(matches)}"
        raise ValueError(error_msg)

    def card_info(self, card_id: int) -> dict[str, Any]:
        """Fetches the information of a card.

        Args:
            card_id: The ID of the card.

        Returns:
            The information of the card.
        """
        params = {"notes": [card_id]}
        return self.invoke("notesInfo", params)
