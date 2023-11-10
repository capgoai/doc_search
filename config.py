import logging
import pathlib

logger: logging.Logger = logging.getLogger(__name__)

db_name: str = "test.db"
data_root_path: pathlib.Path = pathlib.Path("data")
db_path: pathlib.Path = data_root_path / db_name
data_file_name: str = "data.txt"
index_file_name: str = "index.faiss"

# to save faiss
block_size = -1

max_characters: int = 500
k: int = 5
threshold: float = 0.7
