"""A script to import flashcards from markdown files to Anki."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from mankey.anki_connector import AnkiConnector
from mankey.cloze_flashcard import ClozeFlashcard
from mankey.enclosed_flashcard import EnclosedFlashcard
from mankey.question_answer_flashcard import QuestionAnswerFlashcard
from mankey.remnote_flashcard import RemnoteFlashcard


class MDFile(EnclosedFlashcard, RemnoteFlashcard, ClozeFlashcard, QuestionAnswerFlashcard):
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
        if self.has_cloze_flashcards:
            self.create_deck(self.deck_name)
            self.import_cloze_flashcards()
        if self.has_question_answer_flashcards:
            self.create_deck(self.deck_name)
            self.import_question_answer_flashcards()

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
