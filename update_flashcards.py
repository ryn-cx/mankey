"""A script to import flashcards from markdown files to Anki."""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from pathlib import Path
from typing import Any

import markdown
import toml


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

        Just used for debugging purposes

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


class BaseFlashcard:
    """Base class for flashcards."""

    md_file: Path

    def deck_name(self) -> str:
        """Returns the name of the deck."""
        return self.md_file.parent.name

    def get_anki_id_from_line(self, string: str) -> int | None:
        """Get the Anki ID from a string that is a single line."""
        if match_data := re.search(r"\^anki-(\d{13})$", string):
            self.anki_id = int(match_data.group(1))
        else:
            self.anki_id = None

    def strip_single_line_formatting(self, text: str) -> str:
        """Strips extra formatting for a single line of text."""
        if text.count("\n") > 0:
            error_msg = "This function should only be used on strings that are a single line long."
            raise ValueError(error_msg)

        text = text.strip()
        if text.startswith(("-", "#")):
            text = text[1:].strip()
        return text

    def strip_anki_id(self, text: str) -> str:
        """Strips the anki id from a string."""
        return re.sub(r"\^anki-\d{13}", "", text)

    def format_math(self, string: str) -> str:
        """Formats mathjax in a string."""
        return re.sub(r"\$(\S(?:.*?\S)?)\$", r"<anki-mathjax>\1</anki-mathjax>", string)

    def format_img(self, string: str) -> str:
        """Formats images in a string."""
        return re.sub(r"!\[\[(.*?)\]\]", r'<img src="\1">', string)

    def store_media(self, string: str) -> None:
        """Stores media files in a string."""
        for image in re.findall(r"!\[\[(.*?)\]\]", string):
            ANKI_CONNECTOR.store_media_file(image, (MARKDOWN_PATH / image).read_bytes())

    def format_mermaid(self, string: str) -> str:
        """Formats mermaid diagrams in a string."""
        return re.sub(r"```mermaid(.*?)```", r'<div class="mermaid">\1</div>', string, flags=re.DOTALL)

    def raise_if_anki_id_not_defined(self) -> None:
        """Raises an error if the Anki ID is not found."""
        if not self.anki_id:
            error_msg = "Anki ID is not defined."
            raise ValueError(error_msg)


class BaseSingleLineFlashcard(BaseFlashcard):
    """Base class for flashcards that are a single line."""

    def new_line_content(self, file_lines: list[str], line_number: int) -> str:
        self.raise_if_anki_id_not_defined()

        if not file_lines[line_number].endswith(f" ^anki-{self.anki_id}"):
            return f"{file_lines[line_number]} ^anki-{self.anki_id}"

        return file_lines[line_number]


class BaseMultiLineFlashcard(BaseFlashcard):
    """Base class for flashcards that span multiple lines."""

    file_lines: list[str]
    answer_end_line: int
    question: str
    answer: str

    def get_multiline_anki_id(self) -> int | None:
        """Get the Anki ID from a multiline string."""
        # The current line ends with an Anki tag
        if match_data := re.search(r"\^anki-(\d{13})$", self.file_lines[self.answer_end_line]):
            return int(match_data.group(1))
        # The next line exists and it is just an Anki tag
        if len(self.file_lines) > self.answer_end_line + 1 and (
            match_date := re.search(r"^\^anki-(\d{13})$", self.file_lines[self.answer_end_line + 1])
        ):
            return int(match_date.group(1))

        # Unable to find Anki tag
        return None

    def import_flashcard(self) -> None:
        """Imports a flashcard into Anki."""
        ANKI_CONNECTOR.create_deck(self.deck_name())
        self.anki_id = ANKI_CONNECTOR.import_question_answer(self.deck_name(), self.question, self.answer, self.anki_id)

    def new_line_content(self) -> str:
        """Returns the new line content for the file."""
        self.raise_if_anki_id_not_defined()

        if not self.file_lines[self.answer_end_line].endswith(f" ^anki-{self.anki_id}") and not (
            len(self.file_lines) > self.answer_end_line + 1
            and self.file_lines[self.answer_end_line + 1] == f"^anki-{self.anki_id}"
        ):
            if self.file_lines[self.answer_end_line].strip().endswith("```"):
                return f"{self.file_lines[self.answer_end_line]}\n^anki-{self.anki_id}"

            return f"{self.file_lines[self.answer_end_line]} ^anki-{self.anki_id}"
        return self.file_lines[self.answer_end_line]


class HeaderQuestionAnswer(BaseMultiLineFlashcard):
    """Class for flashcards with headers that say "Question" and "Answer"."""

    def __init__(self, md_file: Path, file_lines: list[str], start_line: int) -> None:
        """Initializes the HeaderQuestionAnswer class."""
        self.md_file = md_file
        self.file_lines = file_lines
        self.question_level = len(self.file_lines[start_line].split(" ")[0])
        self.question_start_line = start_line + 1  # Question always starts directly after header
        self.question_end_line = self.get_question_end_line()
        self.answer_start_line = self.question_end_line + 2  # Answer is always after the answer header
        self.answer_end_line = self.get_answer_end_line()
        self.question = self.format_string(self.question_start_line, self.question_end_line)
        self.answer = self.format_string(self.answer_start_line, self.answer_end_line)
        self.anki_id = self.get_multiline_anki_id()

    def get_question_end_line(self) -> int:
        """Get the line number of the end of the question."""
        for line_number, line_content in enumerate(self.file_lines):
            if line_number > self.question_start_line:
                regex = r"#" + "{" + str(self.question_level) + "}" + r"\sAnswer"
                if re.match(regex, line_content):
                    return line_number - 1

        error_msg = "Question end not found"
        raise ValueError(error_msg)

    def get_answer_end_line(self) -> int:
        """Get the line number of the end of the answer."""
        last_line = len(self.file_lines) - 1
        for line_number, line_content in enumerate(self.file_lines):
            # It's easier to seperately check when the last line of the file is reached due to off by 1 errors
            if line_number == last_line:
                return last_line

            if line_number > self.answer_start_line:
                regex = r"#" + "{1," + str(self.question_level) + "}"
                if re.match(regex, line_content):
                    return line_number - 1
                if re.search(r"^\^anki-(\d{13})$", line_content):
                    return line_number - 1

        error_msg = "Answer end not found"
        raise ValueError(error_msg)

    def format_string(self, start_line: int, end_line: int) -> str:
        """Formats a string for Anki."""
        string = "\n".join(self.file_lines[start_line : end_line + 1])
        string = self.strip_anki_id(string)
        string = self.format_math(string)
        string = self.format_img(string)
        string = self.format_mermaid(string)

        # nl2br - Makes new lines in the markdown file show up in Anki
        return markdown.markdown(string, extensions=["nl2br", "tables", "fenced_code"])


class InlineQuestionAnswer(BaseMultiLineFlashcard):
    """Class for flashcards with inline questions and answers."""

    def __init__(self, md_file: Path, file_lines: list[str], start_line: int) -> None:
        """Initializes the InlineQuestionAnswer class."""
        self.md_file = md_file
        self.file_lines = file_lines
        self.question_level = len(self.file_lines[start_line].split("-")[0])
        self.question_start_line = self.get_question_start_line(start_line)
        self.question_end_line = self.get_question_end_line()
        self.answer_start_line = self.get_answer_start_line()
        self.answer_end_line = self.get_answer_end_line()
        self.question = self.format_string(self.question_start_line, self.question_end_line)
        self.answer = self.format_string(self.answer_start_line, self.answer_end_line)
        self.anki_id = self.get_multiline_anki_id()

    def get_question_start_line(self, start_line: int) -> int:
        """Get the line number of the start of the question."""
        # For lines that are just "- Question" start on the next line
        if self.file_lines[start_line].endswith("- Question"):
            return start_line + 1

        # For all other situations include the lines that starts with "- Question"
        return start_line

    def get_question_end_line(self) -> int:
        """Get the line number of the end of the question."""
        for line_number, line_content in enumerate(self.file_lines):
            # Checks all lines after the current line to find an Answer line and then backtracks
            if line_number > self.question_start_line:
                regex = r" " + "{" + str(self.question_level) + "}" + r"-\sAnswer"
                if re.match(regex, line_content):
                    return line_number - 1

        error_msg = "Question end not found"
        raise ValueError(error_msg)

    def get_answer_start_line(self) -> int:
        """Get the line number of the start of the answer."""
        for line_number, line_content in enumerate(self.file_lines):
            # Checks all lines after the current line to find an Answer line
            if line_number > self.question_start_line:
                # If the answer line is just a deliminator ignore it and go to the next line
                if line_content.endswith("- Answer"):
                    return line_number + 1
                # If the answer line includes information include it
                if "- Answer" in line_content:
                    return line_number

        error_msg = "Answer start not found"
        raise ValueError(error_msg)

    def get_answer_end_line(self) -> int:
        """Get the line number of the end of the answer."""
        last_line = len(self.file_lines) - 1
        for line_number, line_content in enumerate(self.file_lines):
            # Pre-check if this is the last line of the file
            # Easier to do this seperate from the if block
            if line_number == last_line:
                return last_line

            if line_number > self.answer_start_line:
                # Find a line with the same number of indentation or less than the question
                if re.match(r" {0," + str(self.question_level) + r"}-|#", line_content):
                    return line_number - 1
                # Find a line that just includes the Anki tag which must be the end of the line
                if re.search(r"^\^anki-(\d{13})$", line_content):
                    return line_number - 1

        error_msg = "Answer end not found"
        raise ValueError(error_msg)

    def format_string(self, start_line: int, end_line: int) -> str:
        """Formats a string for Anki."""
        string = "\n".join(self.file_lines[start_line : end_line + 1])
        string = self.strip_anki_id(string)
        string = self.format_math(string)
        string = self.format_img(string)
        string = self.format_mermaid(string)

        # Removes the question and answer headers on lines that include the question with the header
        # Example: "- Question: Q String" becomes "Q String" and - Answer: A String" becomes "A String"
        string = string.replace("- Question: ", "- ")
        string = string.replace("- Answer: ", "- ")

        split_string = string.split("\n")

        # If the string is only a single line extra stripping can be done
        if len(split_string) == 1:
            split_string[0] = self.strip_single_line_formatting(split_string[0])
        else:
            # Strip the extra indentation that occurs if the question is indented multiple levels
            for line_number, line in enumerate(split_string):
                rep_string = "\t" * (self.question_level)
                split_string[line_number] = line.replace(rep_string, "")

        string = "\n".join(split_string)

        # nl2br - Convert newlines in markdown
        # tables - Converts tables in markdown
        # fenced_code - Converts code blocks in markdown
        return markdown.markdown(string, extensions=["nl2br", "tables", "fenced_code"])


class Cloze(BaseSingleLineFlashcard):
    def __init__(self, md_file: Path, cloze_string: str) -> None:
        """Initializes the Cloze class."""
        self.md_file = md_file
        self.cloze_string = self.format_clozue(cloze_string)
        self.get_anki_id_from_line(cloze_string)

    def format_clozue(self, string: str) -> str:
        """Formats a cloze string for Anki."""
        string = self.format_math(string)
        string = self.strip_single_line_formatting(string)
        string = self.strip_anki_id(string)
        string = self.format_img(string)

        # Count the number of clozures and replace them with Anki syntax
        for cloze_number in range(string.count("**") // 2):
            string = string.replace("**", f"{{{{c{cloze_number+1}::", 1)
            string = string.replace("**", "}}", 1)

        return markdown.markdown(string)

    def import_flashcard(self) -> None:
        """Imports a cloze flashcard into Anki."""
        self.store_media(self.cloze_string)
        ANKI_CONNECTOR.create_deck(self.deck_name())
        self.anki_id = ANKI_CONNECTOR.import_clozure(self.deck_name(), self.cloze_string, self.anki_id)


class Definition(BaseSingleLineFlashcard):
    def __init__(self, md_file: Path, word_definition_string: str) -> None:
        """Initializes the Definition class."""
        self.md_file = md_file
        self.word_definition_string = word_definition_string
        self.get_anki_id_from_line(word_definition_string)

    def format_definition(self, string: str) -> tuple[str, str]:
        """Formats a definition string for Anki."""
        string = self.format_math(string)
        string = self.strip_single_line_formatting(string)
        string = self.strip_anki_id(string)
        string = self.format_img(string)

        if match := re.search(r"\*\*(.*?)\*\*:(.*?)$", string):
            word = match.group(1)
            definition = match.group(2)
        else:
            error_msg = "No regex match for the Word/Question."
            raise ValueError(error_msg)

        return (markdown.markdown(word), markdown.markdown(definition))

    def import_flashcard(self) -> None:
        """Imports a definition flashcard into Anki."""
        word, definition = self.format_definition(self.word_definition_string)
        ANKI_CONNECTOR.create_deck(self.deck_name())
        self.anki_id = ANKI_CONNECTOR.import_definition(self.deck_name(), word, definition, self.anki_id)


class MDFile:
    """Class for markdown files."""

    def __init__(self, md_file: Path) -> None:
        """Initializes the MDFile class."""
        self.md_file = md_file
        self.file_content = md_file.read_text()
        self.file_lines = self.file_content.split("\n")
        self.updated_file_lines = self.file_content.split("\n")

    def import_clozes(self) -> None:
        """Import cloze flashcards from the markdown file."""
        for line_number, line_content in enumerate(self.file_lines):
            if "**" in line_content and not self.is_definition(line_content):
                cloze = Cloze(self.md_file, line_content)
                cloze.import_flashcard()
                self.updated_file_lines[line_number] = cloze.new_line_content(self.file_lines, line_number)

    def import_definitions(self) -> None:
        """Import definition flashcards from the markdown file."""
        for line_number, line_content in enumerate(self.file_lines):
            if self.is_definition(line_content):
                definition = Definition(self.md_file, line_content)
                definition.import_flashcard()
                self.updated_file_lines[line_number] = definition.new_line_content(self.file_lines, line_number)

    def import_header_question_answer(self) -> None:
        """Import header question answer flashcards from the markdown file."""
        for line_number, line_content in enumerate(self.file_lines):
            if re.match(r"^#+\sQuestion", line_content):
                flashcard = HeaderQuestionAnswer(self.md_file, self.file_lines, line_number)
                flashcard.import_flashcard()
                self.updated_file_lines[flashcard.answer_end_line] = flashcard.new_line_content()

    def import_inline_question_answer(self) -> None:
        """Import inline question answer flashcards from the markdown file."""
        for line_number, line_content in enumerate(self.file_lines):
            if re.match(r"^-+\sQuestion", line_content.strip()):
                flashcard = InlineQuestionAnswer(self.md_file, self.file_lines, line_number)
                flashcard.import_flashcard()
                self.updated_file_lines[flashcard.answer_end_line] = flashcard.new_line_content()

    def export_file(self) -> None:
        """Export the markdown file with Anki tags."""
        new_content = "\n".join(self.updated_file_lines)
        if self.file_content != new_content:
            self.md_file.write_text(new_content)

    def is_definition(self, text: str) -> bool:
        """Identify fake cloze flashcards.

        A fake close is a flashcard that is a word or phrase followed by a colon and its definition.
        """
        text = text.strip()

        if text.startswith("-"):
            text = text[1:].strip()

        return text.startswith("**") and len(re.findall(r"\*\*(.*?)\*\*:", text)) == 1


# Load INPUT_DiR from config.toml
CONFIG_FILE = Path("config.toml")
if not CONFIG_FILE.exists():
    error_msg = "The config file does not exist."
    raise FileNotFoundError(error_msg)
LOADED_CONFIG = toml.load(CONFIG_FILE)
MARKDOWN_PATH = LOADED_CONFIG["path"]

DELETE = False
MD_FILES = [MDFile(x) for x in MARKDOWN_PATH.glob("**/*.md")]
ANKI_CONNECTOR = AnkiConnector()


def main() -> None:
    for md_file in MD_FILES:
        md_file.import_clozes()
        md_file.import_definitions()
        md_file.import_header_question_answer()
        md_file.import_inline_question_answer()
        md_file.export_file()


if __name__ == "__main__":
    main()
