import os
import pathlib


db_name: str = "test.db"
data_root_path_str = os.environ.get("DATA_ROOT_PATH")
data_root_path: pathlib.Path = pathlib.Path("data")
db_path: pathlib.Path = data_root_path / db_name
data_file_name: str = "data.txt"
index_file_name: str = "index.faiss"

model_name: str = "intfloat/multilingual-e5-small"

# to save faiss
block_size: int = -1

max_characters: int = 500
k: int = 5
threshold: float = 0.7
