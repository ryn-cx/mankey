# mankey
 Copies flashcards from Markdown to Anki

Uses syntax designed around the way I personally take notes.

- Supported syntaxes
    - A bolded word and followed by its definition will be made into a Basic (and reverse card)
        - Example: **Word**: Definition
    - Clozure style flashcards will be made automatically when bolded words are found
        - Example:The flashcard with **clozure** content
    - Inline question and answer
	    - Example 1
		    - Question: The question
		    - Answer: The answer
		- Example 2
			- Question
				- The first part of the question
				- The second part of the question
			- Answer
				- The first part of the answer
				- The second part of the answer
	- Question and answer headers
		- Example
			# Question
			The question
			# Answer
			The answer
         
Includes basic conversion of markdown to Anki such as inlined LaTeX, mermaid, images and tables.