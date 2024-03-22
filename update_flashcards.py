"""A script to import flashcards from markdown files to Anki."""

from __future__ import annotations

import argparse
import base64
import json
import re
import urllib.request
from functools import cached_property
from pathlib import Path
from typing import Any

import markdown


class AnkiConnector:
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
        if anki_id:
            params = {"notes": [anki_id]}
            result = cls.invoke("notesInfo", params)
            if result == [{}]:
                print(f"Note with id {anki_id} does not exist")
            else:
                cls.update_flashcard(deck_name, question, answer, card_model, anki_id)
        else:
            return cls.add_flashcard(deck_name, question, answer, card_model)


class SharedFlashcard(AnkiConnector):
    def __init__(self, input_dir: str, file_name: str) -> None:
        """Initialize the class with the input directory and file name.

        Args:
            input_dir (str): The directory where the input file is located.
            file_name (str): The name of the input file.
        """
        self.input_dir = input_dir
        self.file_name = file_name

    @cached_property
    def deck_name(self) -> str:
        """Returns the deck name derived from the file name.

        This function removes the input directory prefix and the '.md' suffix from the file name,
        replaces '/' with '::', and returns the result as the deck name.

        Returns:
            str: The deck name.
        """
        return self.file_name.removeprefix(f"{self.input_dir}/").removesuffix(".md").replace("/", "::")

    @cached_property
    def file_lines(self) -> list[str]:
        """Reads the file and returns its lines.

        This function opens the file in read mode with utf-8 encoding, reads the file,
        splits it into lines, and returns the lines.

        Returns:
            List[str]: The lines of the file.
        """
        with Path(self.file_name).open("r", encoding="utf-8") as file:
            return file.read().splitlines()

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

        # This does some general markdown conversion, most importantly it converts tables
        return markdown.markdown(latex_done, extensions=["tables"])

    def import_images(self, line_content: str) -> None:
        """Searches for images in the line content and imports them.

        This function finds all matches of the IMAGE_REGEX in the line content. For each match,
        it constructs the image path and name, checks if the image file exists, and if so, stores the image file.
        If the image file does not exist, it prints a message.

        Args:
            line_content (str): The content of the line to search for images.

        Returns:
            None
        """
        for match in re.finditer(self.IMAGE_REGEX, line_content):
            # Ugly nonsense to deal with partial file paths and complete file paths
            image_name = match.group(1)
            if image_name.startswith("zzz_attachments/"):
                image_path = f"{self.input_dir}/{image_name}"
            else:
                image_name = f"{self.deck_name}/{image_name}"
                image_path = f"{self.input_dir}/zzz_attachments/{image_name}"

            # Relative enough path that should be used as the base of file names
            relative_image_path = image_path.removeprefix(f"{self.input_dir}/")

            if Path(image_path).is_file():
                # Anki does not support slashes in file names so replace them with underscores
                simple_name = relative_image_path.replace("/", "_")
                self.store_media_file(simple_name, Path(image_path).read_bytes())
            else:
                print(f"Unable to find image: {image_path}")

    def split_anki_id(self, answer: str) -> tuple[str, int | None]:
        """Extracts the Anki ID from the answer and removes it.

        This function searches for a pattern '^anki-' followed by 13 digits at the end of the answer.
        If the pattern is found, it extracts the 13 digits as the Anki ID, removes the pattern from the answer,
        and returns the modified answer and the Anki ID. If the pattern is not found, it returns the original answer and
        None.

        Args:
            answer (str): The answer string to extract the Anki ID from.

        Returns:
            tuple[str, int | None]: The modified answer and the Anki ID, or the original answer and None if no Anki ID
            is found.
        """
        anki_id = None
        anki_id_regex = r"\^anki-(\d{13})$"
        if match_data := re.search(anki_id_regex, answer):
            anki_id = int(match_data.group(1))
            answer = re.sub(anki_id_regex, "", answer)
        return answer, anki_id

    def write_file(self) -> None:
        """Writes the file lines to the file.

        This function opens the file in write mode with utf-8 encoding, joins the file lines with newline characters,
        and writes the result to the file.

        Returns:
            None
        """
        with Path(self.file_name).open("w", encoding="utf-8") as file:
            file.write("\n".join(self.file_lines))


class EnclosedFlashcard(SharedFlashcard):
    @cached_property
    def has_enclosed_flashcards(self) -> bool:
        """Checks if the file has valid flashcards.

        This function checks if the flashcard tags are valid and if there are any tags.
        If the tags are invalid or there are no tags, it logs that information and returns False.
        Otherwise, it returns True.

        Returns:
            bool: True if the file has valid flashcards, False otherwise.
        """
        # If there are no tags then there are no flashcards in the file
        if len(self.enclosed_flashcard_tags) == 0:
            return False

        # If the tags are invalid log that information so it can be fixed
        if not all(
            start in ("#flashcard-regular", "#flashcard-reverse")
            and middle == "#flashcard-middle"
            and end == "#flashcard-end"
            for start, middle, end in zip(*[iter(self.enclosed_flashcard_tags)] * 3)
        ):
            print(f"{self.file_name} has invalid flashcard tags")
            return False

        return True

    @cached_property
    def get_enclosed_flashcard_tags_and_lines(self) -> tuple[list[str], list[int]]:
        """Parses the file lines and returns the flashcard tags and their line numbers.

        This function iterates over the lines of the file. For each line, it splits the line into words,
        checks if each word starts with "#flashcard-", and if so, appends the word to flashcard_tags and
        the line number to flashcard_lines. It returns flashcard_tags and flashcard_lines.

        Returns:
            Tuple[List[str], List[int]]: The flashcard tags and their line numbers.
        """
        flashcard_tags: list[str] = []
        flashcard_lines: list[int] = []
        for line_number, line in enumerate(self.file_lines):
            for word in line.split():
                if word.startswith("#flashcard-"):
                    flashcard_tags.append(word)
                    flashcard_lines.append(line_number)
        return flashcard_tags, flashcard_lines

    def import_enclosed_flashcards(self) -> None:
        """Imports the flashcards.

        This function iterates over the flashcard tags and lines in groups of 3. For each group,
        it parses the flashcard, checks if the flashcard has an Anki ID, and if so, updates the flashcard,
        otherwise, adds the flashcard. After each flashcard is processed, it writes the file.

        Returns:
            None
        """
        for i in range(0, len(self.enclosed_flashcard_tags), 3):
            tags_group = self.enclosed_flashcard_tags[i : i + 3]
            lines_group = self.enclosed_flashcard_lines[i : i + 3]
            card_model = "Basic (and reversed card)" if tags_group[0] == "#flashcard-reverse" else "Basic"

            question, answer, anki_id = self.parse_enclosed_flashcard(lines_group, tags_group)

            anki_id = self.import_flashcard(self.deck_name, question, answer, card_model, anki_id)

            if anki_id:
                self.file_lines[lines_group[2]] += f" ^anki-{anki_id}"

            # It's better to write the file after each flashcard is added just in case an issue happens half way through
            self.write_file()

    @cached_property
    def enclosed_flashcard_tags(self) -> list[str]:
        """Returns the flashcard tags.

        This function calls the _parse_flashcards method and returns the first element of the result.

        Returns:
            List[str]: The flashcard tags.
        """
        return self.get_enclosed_flashcard_tags_and_lines[0]

    @cached_property
    def enclosed_flashcard_lines(self) -> list[int]:
        """Returns the flashcard lines.

        This function calls the _parse_flashcards method and returns the second element of the result.

        Returns:
            List[int]: The flashcard lines.
        """
        return self.get_enclosed_flashcard_tags_and_lines[1]

    def parse_enclosed_flashcard(
        self,
        lines_group: list[int],
        tags_group: list[str],
    ) -> tuple[str, str, int | None]:
        """Parses a flashcard and returns the question, answer, and Anki ID.

        This function joins the lines of the flashcard, imports the images, replaces the image paths,
        splits the content into question and answer, removes the flashcard tags, splits the Anki ID from the answer,
        converts the question and answer from markdown to Anki's format, and returns the question, answer, and Anki ID.

        Args:
            lines_group (list[int]): The line numbers of the flashcard.
            tags_group (list[str]): The flashcard tags.

        Returns:
            tuple[str, str, int | None]: The question, answer, and Anki ID of the flashcard.
        """
        line_content = "\n".join(self.file_lines[lines_group[0] : lines_group[2] + 1])
        self.import_images(line_content)
        line_content = re.sub(
            self.IMAGE_REGEX,
            lambda match: match.group(0).replace("/", "_"),
            line_content,
        )

        question, answer = line_content.split("#flashcard-middle")
        question = question.replace(tags_group[0], "")
        answer = answer.replace(tags_group[2], "")

        answer, anki_id = self.split_anki_id(answer)

        question = self.markdown_to_anki(question)
        answer = self.markdown_to_anki(answer)
        return question, answer, anki_id


class RemnoteFlashcard(SharedFlashcard):
    def import_remnote_flashcards(self) -> None:
        for line_number, line_content in enumerate(self.file_lines):
            if "::" in line_content or ":::" in line_content:
                if ":::" in line_content:
                    question, answer = line_content.split(":::")
                    card_model = "Basic"
                else:
                    question, answer = line_content.split("::")
                    card_model = "Basic (and reversed card)"
                answer, anki_id = self.split_anki_id(answer)

                anki_id = self.import_flashcard(self.deck_name, question, answer, card_model, anki_id)

                if anki_id:
                    self.file_lines[line_number] += f" ^anki-{anki_id}"
                # It's better to write the file after each flashcard is added just in case an issue happens half way through
                self.write_file()

    @cached_property
    def has_remnote_flashcards(self) -> bool:
        return any("::" in line or ":::" in line for line in self.file_lines)


class MDFile(EnclosedFlashcard, RemnoteFlashcard):
    """A class to import flashcards from a markdown file to Anki."""

    IMAGE_REGEX = r"!\[.*?\]\((.*?)\)"

    def import_file(self) -> None:
        """Imports the flashcards from the file.

        This function checks if the file has flashcards. If it does, it creates a deck and imports the flashcards.

        Returns:
            None
        """
        if self.has_enclosed_flashcards:
            self.create_deck(self.deck_name)
            self.import_enclosed_flashcards()
        if self.has_remnote_flashcards:
            self.create_deck(self.deck_name)
            self.import_remnote_flashcards()

    def anki_ids(self) -> list[int]:
        """Returns the Anki IDs of the flashcards.

        This function iterates over the flashcard tags and lines in groups of 3. For each group,
        it parses the flashcard and returns the Anki ID if it exists.

        Returns:
            List[int]: The Anki IDs of the flashcards.
        """
        anki_ids: list[int] = []
        for line in self.file_lines:
            if match_data := re.search(r"\^anki-(\d{13})", line):
                anki_ids.append(int(match_data.group(1)))
        return anki_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="Update flashcards")
    parser.add_argument("--input_dir", type=str, default="input", help="Input directory", required=True)
    parser.add_argument("--delete", action="store_true", help="Delete Anki entries not found in the input directory")

    args = parser.parse_args()
    input_dir = args.input_dir
    delete = args.delete

    anki_ids: list[int] = []
    # Import everything in one loops
    for md_file in Path(input_dir).glob("**/*.md"):
        md_object = MDFile(input_dir, str(md_file))
        md_object.import_file()
        anki_ids += md_object.anki_ids()

    if delete:
        notes_to_delete = [item for item in AnkiConnector.manki_notes() if item not in anki_ids]
        print(f"Deleting {len(notes_to_delete)} notes")
        delete_confirmation = input("Are you sure you want to delete these notes? y/N")
        if delete_confirmation.lower() == "y":
            AnkiConnector.delete_notes(notes_to_delete)


if __name__ == "__main__":
    main()
