"""Language codes as the engine takes them (light: the server imports it)."""

# Three-letter codes (ISO 639-2) of languages the models know by their two-letter one: with
# "glg" the Galician models, clitics, numbers and syllables would all be missed.
TWO_LETTERS = {
    "glg": "gl", "spa": "es", "por": "pt", "eng": "en", "fra": "fr", "fre": "fr",
    "deu": "de", "ger": "de", "ita": "it", "cat": "ca", "eus": "eu", "baq": "eu",
}  # fmt: skip
