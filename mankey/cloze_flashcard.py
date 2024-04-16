from __future__ import annotations

from functools import cached_property

from .shared_flashcard import SharedFlashcard


class ClozeFlashcard(SharedFlashcard):
    # TODO: This is terrible and hardcoded to a max of 5 clozures
    def clozify(self, index: int) -> str:
        pattern = [
            "{",
            "{c1::",
            "}",
            "}",
            "{",
            "{c2::",
            "}",
            "}",
            "{",
            "{c3::",
            "}",
            "}",
            "{",
            "{c4::",
            "}",
            "}",
            "{",
            "{c5::",
            "}",
            "}",
            "{c6::",
            "}",
            "}",
            "{c7::",
            "}",
            "}",
            "{c8::",
            "}",
            "}",
        ]
        return pattern[index]

    def import_cloze_flashcards(self) -> None:
        output = self.file_lines.copy()
        for line_number, line_content in enumerate(self.file_lines):
            if "**" in line_content:
                asterisk_number = 0
                for character in line_content:
                    if character == "*" and line_content[line_content.index(character) - 1] != "\\":
                        output[line_number] = output[line_number].replace("*", self.clozify(asterisk_number), 1)
                        asterisk_number += 1

                question = output[line_number].strip()
                # If - or # is the first character remove it
                if question.startswith("-") or question.startswith("#"):
                    question = question[1:].strip()

                question, anki_id = self.split_anki_id(question)

                anki_id = self.import_cloze_flashcard(self.deck_name, question, anki_id)

                if anki_id:
                    output[line_number] = output[line_number].split("^anki-")[0].strip()
                    self.file_lines[line_number] += f" ^anki-{anki_id}"
                # It's better to write the file after each flashcard is added just in case an issue happens half way through
                self.write_file()

    @cached_property
    def has_cloze_flashcards(self) -> bool:
        return any("**" in line for line in self.file_lines)
