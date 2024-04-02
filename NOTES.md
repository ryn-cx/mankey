# Mermaid support
Need to manually copy mermaid.min.js into Anki's media folder
Need to modify all of the cards (not the notes) to load mermaid and execute it. Add the following to each card.
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.0/dist/mermaid.min.js"></script>
<script>mermaid.init();</script>