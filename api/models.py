from pydantic import BaseModel
import calendar
import time
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from enum import IntEnum
import logging
from typing import Optional
from config import data_file_name, index_file_name, block_size

logger = logging.getLogger(__name__)


class DocumentState(IntEnum):
    DEFAULT = 0
    UPLOADED = 1
    PROCESSED = 2
    INDEX_BUILT = 3


class DocumentExistsExcpetion(Exception):
    """Exception raised when attempting to insert a document that already exists."""

    pass




@dataclass
class DocSource:
    doc_path: Path
    file_name: str
    data_file_name: str = data_file_name
    index_file_name: str = index_file_name
    block_size: int = block_size

    def __post_init__(self):
        self.doc_path.mkdir(parents=True, exist_ok=True)

    def save_data(self, data: str):
        with open(self.doc_path / self.data_file_name, "w") as f:
            f.write(data)

    def save_index(self, index: bytes):
        with open(self.doc_path / self.index_file_name, "wb") as f:
            f.write(index)

    def save_doc(self, doc: bytes):
        with open(self.doc_path / self.file_name, "wb") as f:
            f.write(doc)

    def read_data(self) -> str:
        with open(self.doc_path / self.data_file_name, "r") as f:
            return f.read()

    def read_index(self) -> bytes:
        with open(self.doc_path / self.index_file_name, "rb") as f:
            return f.read()

    def read_doc(self) -> bytes:
        with open(self.doc_path / self.file_name, "rb") as f:
            return f.read()


class Doc(BaseModel):
    doc_name: str
    doc_type: str
    uid: int
    file_size: int
    doc_id: str
    create_at: int
    update_at: int
    state: DocumentState = DocumentState.DEFAULT


    def save_db(self, db_path: Path):
        try:
            # Connect to the SQLite database and insert the document record
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO docs (uid, doc_id, doc_name, doc_type, size, state, create_at, update_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self.uid,
                        self.doc_id,
                        self.doc_name,
                        self.doc_type,
                        self.file_size,
                        self.state,
                        self.create_at,
                        self.update_at,
                    ),
                )
        except sqlite3.IntegrityError as e:
            raise DocumentExistsExcpetion(
                f"The document with ID {self.doc_id} already exists."
            ) from e

    @classmethod
    def exists_with_doc_id(cls, db_path: Path, doc_id: str) -> bool:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            # Create a cursor object using the cursor() method
            cursor = conn.cursor()

            # Prepare the query
            query = "SELECT 1 FROM docs WHERE doc_id=? LIMIT 1"

            # Execute the SQL query
            cursor.execute(query, (doc_id,))

            # Return True if a record is found, False otherwise
            return cursor.fetchone() is not None

    
    @classmethod
    def update_state_with_doc_id(cls, db_path: Path, doc_id: str, new_state: DocumentState):
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            query = "UPDATE docs SET state=?, update_at=? WHERE doc_id=?"
            cursor.execute(
                query, (new_state.value, calendar.timegm(time.gmtime()), doc_id)
            )
            conn.commit()

    @classmethod
    def get_by_doc_id(cls, db_path: Path, doc_id: str) -> Optional["Doc"]:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            # Create a cursor object using the cursor() method
            cursor = conn.cursor()

            # Prepare the query
            query = "SELECT uid, doc_id, doc_name, doc_type, size, state, create_at, update_at FROM docs WHERE doc_id=? LIMIT 1"

            # Execute the SQL query
            cursor.execute(query, (doc_id,))

            # Fetch the first row of the query result
            row = cursor.fetchone()

            # Return a new Doc object if a row was returned, None otherwise
            if row:
                return cls(
                    uid=row[0],
                    doc_id=row[1],
                    doc_name=row[2],
                    doc_type=row[3],
                    file_size=row[4],
                    state=row[5],
                    create_at=row[6],
                    update_at=row[7],
                )
            else:
                logger.error("No document found with doc_id: %s", doc_id)
                return None

    @classmethod
    def delete_with_doc_id(cls, db_path: Path, doc_id: str) -> None:
        # Connect to the SQLite database
        with sqlite3.connect(db_path) as conn:
            # Create a cursor object using the cursor() method
            cursor = conn.cursor()

            # Prepare the query
            query = "DELETE FROM docs WHERE doc_id=?"
            cursor.execute(query, (doc_id,))
            conn.commit()
