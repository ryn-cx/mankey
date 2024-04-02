from __future__ import annotations

import re
from functools import cached_property

from .shared_flashcard import SharedFlashcard


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
                if word.startswith(("#flashcard-regular", "#flashcard-reverse", "#flashcard-middle", "#flashcard-end")):
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

        return question, answer, anki_id
