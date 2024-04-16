from __future__ import annotations

from functools import cached_property

from .shared_flashcard import SharedFlashcard


class QuestionAnswerFlashcard(SharedFlashcard):
    def import_question_answer_flashcards(self) -> None:
        """Parses the file lines and returns the flashcard tags and their line numbers.

        This function iterates over the lines of the file. For each line, it splits the line into words,
        checks if each word starts with "#flashcard-", and if so, appends the word to flashcard_tags and
        the line number to flashcard_lines. It returns flashcard_tags and flashcard_lines.

        Returns:
            Tuple[List[str], List[int]]: The flashcard tags and their line numbers.
        """
        self.question = ""
        self.answer = ""
        self.question_mode = False
        self.answer_mode = False
        depth = 0
        number_of_lines = len(self.file_lines)
        code_block = False
        for line_number, line_content in enumerate(self.file_lines):
            cleaned_line_content = line_content.replace("#", "").strip()
            # Check if the current line is part of the note
            if not code_block:
                part_of_note = self.valid_depth(line_content, depth)

            if "```" in line_content:
                code_block = not code_block

            if cleaned_line_content.startswith("Question"):
                self.export_card_if_complete(self.question, self.answer, number_of_lines, line_number, part_of_note)
                self.question_mode = True
                self.answer_mode = False
                depth = line_content.count("#")
                continue
            elif cleaned_line_content.startswith("Answer"):
                self.question_mode = False
                self.answer_mode = True
                continue

            if self.question_mode:
                self.question += "\n" + line_content
            elif self.answer_mode and part_of_note:
                self.answer += "\n" + line_content

            self.export_card_if_complete(self.question, self.answer, number_of_lines, line_number, part_of_note)

    def export_card_if_complete(
        self, question: str, answer: str, number_of_lines: int, line_number: int, part_of_note: bool
    ):
        if self.answer_mode and (not part_of_note or line_number == number_of_lines - 1):
            offset = 0 if line_number == number_of_lines - 1 else 1

            answer, anki_id = self.split_anki_id(answer)
            anki_id = self.import_flashcard(self.deck_name, question, answer, "Basic", anki_id)
            if anki_id:
                self.file_lines[line_number - offset] = self.file_lines[line_number - offset].split("^anki-")[0].strip()
                self.file_lines[line_number - offset] += f" ^anki-{anki_id}"

            # Cleans up old messy stuff that shouldn't exist after this is ran once
            split = self.file_lines[line_number - offset].split("^anki-")
            self.file_lines[line_number - offset] = split[0].strip() + " ^anki-" + split[-1].strip()

            # It's better to write the file after each flashcard is added just in case an issue happens half way through
            self.write_file()
            self.question_mode = False
            self.answer_mode = False
            self.question = ""
            self.answer = ""

    def valid_depth(self, line: str, number_to_check: int):
        """Checks if a line starts with at most three '#' symbols.

        Args:
            line (str): The line to check.

        Returns:
            bool: True if the line starts with at most three '#' symbols, False otherwise.
        """
        if "```" in line:
            print("PAUSE")
        count = 0
        for char in line:
            if char == "#":
                count += 1
            else:
                break

        # It should only be false when there are # and the number of # is less than
        return count == 0 or count > number_to_check

    @cached_property
    def has_question_answer_flashcards(self) -> bool:
        # Check if any line contains just the string Question and Answer ignoring # in the line
        found_question = False
        found_answer = False
        for line in self.file_lines:
            cleaned = line.replace("#", "").strip()
            if cleaned == "Question":
                found_question = True
            if cleaned == "Answer":
                found_answer = True

        return found_question and found_answer
