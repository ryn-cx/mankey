from __future__ import annotations

import re
from functools import cached_property
from pathlib import Path

import markdown

from .anki_connector import AnkiConnector


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
        deck_name = Path(self.file_name).relative_to(Path(self.input_dir).parent)
        return str(deck_name).removesuffix(".md").replace("/", "::")

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
