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
        question = ""
        answer = ""
        question_mode = False
        answer_mode = False
        depth = 0
        number_of_lines = len(self.file_lines)
        for line_number, line_content in enumerate(self.file_lines):
            cleaned_line_content = line_content.replace("#", "").strip()
            if cleaned_line_content == "Question":
                question_mode = True
                answer_mode = False
                depth = line_content.count("#")
                continue
            elif cleaned_line_content == "Answer":
                question_mode = False
                answer_mode = True
                continue

            valid_depth = self.valid_depth(line_content, depth)
            if question_mode:
                question += "\n" + line_content
            elif answer_mode and valid_depth:
                answer += "\n" + line_content

            if (answer_mode and not valid_depth) or line_number == number_of_lines - 1:
                answer, anki_id = self.split_anki_id(answer)
                anki_id = self.import_flashcard(self.deck_name, question, answer, "Basic", anki_id)
                if anki_id:
                    self.file_lines[line_number - 1] += f" ^anki-{anki_id}"

                # It's better to write the file after each flashcard is added just in case an issue happens half way through
                self.write_file()
                question_mode = False
                answer_mode = False
                question = ""
                answer = ""

    def valid_depth(self, line: str, number_to_check: int):
        """Checks if a line starts with at most three '#' symbols.

        Args:
            line (str): The line to check.

        Returns:
            bool: True if the line starts with at most three '#' symbols, False otherwise.
        """
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
