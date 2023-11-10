import os
import sqlite3
from config import db_path, model_name
from sentence_transformers import SentenceTransformer

SentenceTransformer(model_name)
# Desc: Create and initialize the database

if os.path.exists(db_path):
    os.remove(db_path)

table_creation_queries = [
    """
    CREATE TABLE IF NOT EXISTS docs
    (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        uid       INTEGER NOT NULL DEFAULT 0,
        doc_id    TEXT    NOT NULL UNIQUE DEFAULT '',
        doc_name  TEXT    NOT NULL DEFAULT '',
        doc_type  TEXT    NOT NULL DEFAULT '',
        state     INTEGER NOT NULL DEFAULT 0,
        size      INTEGER NOT NULL DEFAULT 0,
        create_at INTEGER NOT NULL DEFAULT 0,
        update_at INTEGER NOT NULL DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS messages
    (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        uid       INTEGER NOT NULL DEFAULT 0,
        doc_id    TEXT    NOT NULL DEFAULT '',
        role      TEXT    NOT NULL DEFAULT '',
        content   TEXT    NOT NULL DEFAULT '',
        create_at INTEGER NOT NULL
    );
    """
]


# Create and initialize the database
with sqlite3.connect(db_path) as conn:
    cur = conn.cursor()
    for query in table_creation_queries:
        cur.execute(query)
    conn.commit()

    # Fetch and print table information
    res = cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    result = res.fetchall()