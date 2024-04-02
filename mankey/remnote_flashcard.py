from __future__ import annotations

from functools import cached_property

from .shared_flashcard import SharedFlashcard


class RemnoteFlashcard(SharedFlashcard):
    def import_remnote_flashcards(self) -> None:
        for line_number, line_content in enumerate(self.file_lines):
            if "::" in line_content or ":::" in line_content:
                if ":::" in line_content:
                    question, answer = line_content.split(":::")
                    card_model = "Basic (and reversed card)"
                else:
                    question, answer = line_content.split("::")
                    card_model = "Basic"
                answer, anki_id = self.split_anki_id(answer)

                anki_id = self.import_flashcard(self.deck_name, question, answer, card_model, anki_id)

                if anki_id:
                    self.file_lines[line_number] += f" ^anki-{anki_id}"
                # It's better to write the file after each flashcard is added just in case an issue happens half way through
                self.write_file()

    @cached_property
    def has_remnote_flashcards(self) -> bool:
        return any("::" in line or ":::" in line for line in self.file_lines)
