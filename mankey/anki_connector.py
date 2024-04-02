"""Interface for interacting with Anki."""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from typing import Any

from markdown import markdown


class AnkiConnector:
    """Interface for interacting with Anki."""

    IMAGE_REGEX = r"!\[.*?\]\((.*?)\)"

    @classmethod
    def request(cls, action: str, **params: Any) -> dict[str, Any]:
        """Constructs a request dictionary with the given action, parameters, and version.

        Args:
            action (str): The action to be included in the request.
            params (Any): Additional keyword arguments to be included in the request parameters.

        Returns:
            Dict[str, Any]: The constructed request dictionary.
        """
        return {"action": action, "params": params, "version": 6}

    @classmethod
    def invoke(cls, action: str, params: Any) -> Any:
        """Sends a request and returns the result.

        This function constructs a request with the given action and parameters, sends the request,
        checks the response, and returns the result. If the response is not valid, it raises a ValueError.

        Args:
            action (str): The action to be included in the request.
            params (Any): Additional arguments to be included in the request parameters.

        Returns:
            Any: The result from the response.

        Raises:
            ValueError: If the response is not valid.
            URLError: If the request fails.
        """
        request_json = json.dumps(cls.request(action, **params)).encode("utf-8")
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

        raise ValueError(error_message)

    @classmethod
    def manki_notes(cls) -> list[int]:
        """Fetches the notes tagged with 'mankey' from Anki.

        Returns:
            list[int]: A list of note IDs.
        """
        params = {"query": "tag:mankey"}
        return cls.invoke("findNotes", params)

    @classmethod
    def delete_notes(cls, notes: list[int]) -> None:
        """Deletes the specified notes from Anki.

        Args:
            notes (list[int]): A list of note IDs to delete.
        """
        params = {"notes": notes}
        cls.invoke("deleteNotes", params)

    @classmethod
    def model_names(cls) -> list[str]:
        """Fetches the model names from Anki.

        Returns:
            list[str]: A list of model names.
        """
        return cls.invoke("modelNames", {})

    @classmethod
    def create_deck(cls, deck_name: str) -> None:
        """Creates a deck with the name stored in self.deck_name.

        This function constructs a request with the action "createDeck" and the parameter "deck" set to self.deck_name,
        and sends the request using the invoke method. If the deck already exists, nothing happens.

        Returns:
            None
        """
        # For simplicity just create the deck without checking if it exists, if it exists nothing happens
        params = {"deck": deck_name}
        cls.invoke("createDeck", params)

    @classmethod
    def store_media_file(cls, file_name: str, data: bytes) -> None:
        """Stores a media file.

        This function constructs a request with the action "storeMediaFile", the file name, and the base64 encoded data,
        and sends the request using the invoke method.

        Args:
            file_name (str): The name of the file to be stored.
            data (bytes): The data of the file to be stored.

        Returns:
            None
        """
        params = {
            "filename": file_name,
            "data": base64.b64encode(data).decode("utf-8"),
        }
        cls.invoke("storeMediaFile", params)

    @classmethod
    def add_flashcard(cls, deck_name: str, question: str, answer: str, card_model: str) -> int:
        """Adds a flashcard.

        This function constructs a request with the action "addNote", the deck name, the model name "Basic",
        and the question and answer, and sends the request using the invoke method. It returns the result of the
        request.

        Args:
            deck_name (str): The name of the deck to add the flashcard to.
            question (str): The question of the flashcard.
            answer (str): The answer of the flashcard.
            card_model (str): The model name of the flashcard.

        Returns:
            int: The result of the request.
        """
        params = {
            "note": {
                "deckName": deck_name,
                "modelName": card_model,
                "fields": {
                    "Front": question,
                    "Back": answer,
                },
                "tags": ["mankey"],
            },
        }
        return cls.invoke("addNote", params)

    @classmethod
    def update_flashcard(cls, deck_name: str, question: str, answer: str, card_model: str, anki_id: int) -> int:
        """Updates a flashcard.

        This function constructs a request with the action "updateNoteFields", the Anki ID, and the question and answer,
        and sends the request using the invoke method. It returns the result of the request.

        Args:
            question (str): The new question of the flashcard.
            answer (str): The new answer of the flashcard.
            card_model (str): The model name of the flashcard.
            anki_id (int): The Anki ID of the flashcard to be updated.

        Returns:
            int: The result of the request.
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
        return cls.invoke("updateNote", params)

    @classmethod
    def markdown_to_anki(cls, string: str) -> str:
        """Converts a markdown string to Anki's format.

        This function takes a markdown string as input, converts LaTeX to Anki's MathJax format,
        and then converts the string from markdown to HTML using the markdown library.
        It returns the converted string.

        Args:
            string (str): The markdown string to be converted.

        Returns:
            str: The converted string in Anki's format.
        """
        # Convert the LaTeX to Anki's MathJax format
        pattern = re.compile(r"\$([^\s\n].*?[^\s\n])\$", re.MULTILINE)
        replacement = r"<anki-mathjax>\1</anki-mathjax>"
        latex_done = re.sub(pattern, replacement, string)

        mermaid_identifier = "!!!THIS IS TEMPORARY PLACEHOLDER TEXT FOR MERMAID!!!"
        mermaid_string = ""
        if "```mermaid" in latex_done:
            # Get text between ```mermaid and ``` and put it into a variable
            regex_match = re.search(r"```mermaid(.*?)```", latex_done, re.DOTALL)
            if regex_match:
                mermaid_string = regex_match.group(1)
            latex_done = latex_done.replace(f"```mermaid{mermaid_string}```", mermaid_identifier)

        markdown_text = markdown(latex_done, extensions=["tables"])

        if mermaid_string:
            # Replace the placeholder text with the mermaid string
            fixed_mermaid = '<div class="mermaid">' + mermaid_string + "</div>"
            markdown_text = markdown_text.replace(mermaid_identifier, fixed_mermaid)

        # This does some general markdown conversion, most importantly it converts tables
        return markdown_text

    @classmethod
    def import_flashcard(
        cls, deck_name: str, question: str, answer: str, card_model: str, anki_id: int | None
    ) -> int | None:
        """Imports a flashcard.

        This function constructs a request with the action "addNote", the deck name, the model name "Basic",
        and the question and answer, and sends the request using the invoke method. It returns the result of the
        request.

        Args:
            question (str): The question of the flashcard.
            answer (str): The answer of the flashcard.
            card_model (str): The model name of the flashcard.

        Returns:
            None
        """
        question = cls.markdown_to_anki(question)
        answer = cls.markdown_to_anki(answer)
        if anki_id:
            params = {"notes": [anki_id]}
            result = cls.invoke("notesInfo", params)
            if result == [{}]:
                print(f"Note with id {anki_id} does not exist")
            else:
                cls.update_flashcard(deck_name, question, answer, card_model, anki_id)
        else:
            return cls.add_flashcard(deck_name, question, answer, card_model)

    @classmethod
    def import_cloze_flashcard(cls, deck_name: str, question: str, anki_id: int | None) -> int | None:
        """Imports a flashcard.

        This function constructs a request with the action "addNote", the deck name, the model name "Basic",
        and the question and answer, and sends the request using the invoke method. It returns the result of the
        request.

        Args:
            question (str): The question of the flashcard.
            answer (str): The answer of the flashcard.
            card_model (str): The model name of the flashcard.

        Returns:
            None
        """
        if anki_id:
            params = {"notes": [anki_id]}
            result = cls.invoke("notesInfo", params)
            if result == [{}]:
                print(f"Note with id {anki_id} does not exist")
            else:
                cls.update_cloze_flashcard(deck_name, question, anki_id)
        else:
            return cls.add_cloze_flashcard(deck_name, question)

    @classmethod
    def add_cloze_flashcard(cls, deck_name: str, question: str) -> int:
        """Adds a flashcard.

        This function constructs a request with the action "addNote", the deck name, the model name "Basic",
        and the question and answer, and sends the request using the invoke method. It returns the result of the
        request.

        Args:
            deck_name (str): The name of the deck to add the flashcard to.
            question (str): The question of the flashcard.
            answer (str): The answer of the flashcard.
            card_model (str): The model name of the flashcard.

        Returns:
            int: The result of the request.
        """
        params = {
            "note": {
                "deckName": deck_name,
                "modelName": "Cloze",
                "fields": {
                    "Text": question,
                },
                "tags": ["mankey"],
            },
        }
        return cls.invoke("addNote", params)

    @classmethod
    def update_cloze_flashcard(cls, deck_name: str, question: str, anki_id: int) -> int:
        """Updates a flashcard.

        This function constructs a request with the action "updateNoteFields", the Anki ID, and the question and answer,
        and sends the request using the invoke method. It returns the result of the request.

        Args:
            question (str): The new question of the flashcard.
            answer (str): The new answer of the flashcard.
            card_model (str): The model name of the flashcard.
            anki_id (int): The Anki ID of the flashcard to be updated.

        Returns:
            int: The result of the request.
        """
        params = {
            "note": {
                "deckName": deck_name,
                "id": anki_id,
                "modelName": "Cloze",
                "fields": {
                    "Text": question,
                },
                "tags": ["mankey"],
            },
        }
        return cls.invoke("updateNote", params)
