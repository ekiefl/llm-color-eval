import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS descriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hex_code TEXT NOT NULL,
    describer TEXT NOT NULL,
    max_words INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS guesses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description_id INTEGER NOT NULL REFERENCES descriptions(id),
    guesser TEXT NOT NULL,
    hex_code TEXT NOT NULL,
    score REAL NOT NULL,
    delta_e REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """Open the results database, creating the schema if needed.

    Args:
        path: Path of the SQLite database file.

    Returns:
        An open connection with foreign key enforcement enabled.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def insert_description(
    conn: sqlite3.Connection, hex_code: str, describer: str, max_words: int, text: str
) -> int:
    """Record a description of a color.

    Args:
        conn: Open results database connection.
        hex_code: The color that was described.
        describer: Name of the model that wrote the description.
        max_words: Word budget the description was written under.
        text: The description.

    Returns:
        The new row's id.
    """
    cursor = conn.execute(
        "INSERT INTO descriptions (hex_code, describer, max_words, text) VALUES (?, ?, ?, ?)",
        (hex_code, describer, max_words, text),
    )
    conn.commit()
    return cursor.lastrowid


def insert_guess(
    conn: sqlite3.Connection,
    description_id: int,
    guesser: str,
    hex_code: str,
    score: float,
    delta_e: float,
) -> int:
    """Record a guess made from a stored description.

    Args:
        conn: Open results database connection.
        description_id: Id of the description the guess was made from.
        guesser: Name of the model that made the guess.
        hex_code: The guessed color.
        score: Dialed similarity score between the source color and the guess.
        delta_e: CIEDE2000 distance between the source color and the guess.

    Returns:
        The new row's id.
    """
    cursor = conn.execute(
        "INSERT INTO guesses (description_id, guesser, hex_code, score, delta_e)"
        " VALUES (?, ?, ?, ?, ?)",
        (description_id, guesser, hex_code, score, delta_e),
    )
    conn.commit()
    return cursor.lastrowid
