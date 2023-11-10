import io
import re
import faiss
import logging
import json
import numpy as np
import numpy.typing as npt
from PyPDF2 import PdfReader
from semantic_text_splitter import CharacterTextSplitter
from config import min_characters, max_characters, k, threshold
from typing import Protocol, List, Set, Tuple
from .models import DocSource

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


class AI(Protocol):
    def ask1(self, prompt: str) -> str:
        ...

    def encode(self, text: str) -> npt.NDArray[np.float32]:
        ...


def get_prompt(context: str, query_str: str) -> str:
    return (
        f"<Context>: {context}\n"
        "<Instruction>: Using the provided chunk_id(s) in the <Context> above, "
        "write a response for the given query. "
        "Be concise. Be precise. Remove irrelevant information.\n "
        "Provide infomation on multiple time periods if available. "
        "Do NOT show chunks without available information."
        "Make sure to cite the chunk_id. Must return the output in JSON, "
        "return format should be \{ answer: <response>, sources: [<chunk_id>] \}\n"
        f"<Query>: {query_str}\n"
        "Your answer:\n"
    )


def parse_chunk_id(chunk_id: str) -> int:
    if isinstance(chunk_id, int):
        c_id_int = chunk_id
    elif isinstance(chunk_id, str):
        try:
            c_id_int = int(chunk_id)
        except Exception as e:
            all_nums = re.findall(r"\d+", chunk_id)[-1]
            if len(all_nums) > 0:
                c_id_int = int(all_nums[-1])
            else:
                raise ValueError(f"chunk_id does not contain number: {chunk_id}")
    else:
        raise ValueError(f"chunk_id is not int or str: {chunk_id}")
    return c_id_int


def parse_ai_answer(answer: str) -> Tuple[str, Set[int]]:
    try:
        llm_responses = json.loads(answer)
        assert "answer" in llm_responses, "llm response does not have responses key"
        assert "sources" in llm_responses, "llm response does not have chunk_ids key"
        chunk_ids = llm_responses["sources"]
        assert isinstance(chunk_ids, list), "llm response is not a list"
        assert isinstance(llm_responses["answer"], str), "llm response is not a string" 
        return llm_responses["answer"], set(parse_chunk_id(cid) for cid in chunk_ids)
        
    except Exception as e:
        logger.exception(f"failed to parse llm result: {answer}")
        raise Exception("failed to parse llm result", e)



def parse_ai_answer_old(answer: str) -> [(int, str)]:
    chunk_answers = []
    try:
        llm_responses = json.loads(answer)
        assert isinstance(llm_responses, list), "llm response is not a list"
        for llm_response in llm_responses:
            c_id_int = parse_chunk_id(llm_response["chunk_id"])
            chunk_answers.append((c_id_int, llm_response["response"]))
    except Exception as e:
        logger.exception("failed to parse llm result")
        raise Exception("failed to parse llm result", e)

    logger.info(chunk_answers)
    return chunk_answers


def process_doc(doc_source: DocSource, data: bytes) -> List[str]:
    reader = PdfReader(io.BytesIO(data))

    def remove_breaks(text: str) -> str:
        # replace \n and \r to spaces and longer spaces to single space
        return re.sub(r"\s+", " ", text.replace("\r", " "))

    page_texts = [remove_breaks(page.extract_text()) for page in reader.pages]
    full_text = " ".join(page_texts)

    splitter = CharacterTextSplitter()
    chunks = splitter.chunks(full_text, chunk_capacity=(min_characters, max_characters))

    doc_source.save_data("\n".join(chunks))
    return chunks


def create_store(doc_source: DocSource, ai: AI, chunks: List[str]) -> None:
    embeddings = [ai.encode(chunk) for chunk in chunks]
    index = faiss.IndexFlatL2(len(embeddings[0]))
    faiss.normalize_L2(np.array(embeddings))

    index.add(np.array(embeddings))
    buffer = io.BytesIO()
    writer = faiss.PyCallbackIOWriter(buffer.write)
    faiss.write_index(index, writer)
    del writer
    doc_source.save_index(buffer.getvalue())


def query_item(doc_source: DocSource, ai: AI, query: str) -> [(str, str)]:
    buffer = doc_source.read_index()
    reader = faiss.PyCallbackIOReader(io.BytesIO(buffer).read)
    index = faiss.read_index(reader)
    query_embedding = ai.encode(query)
    faiss.normalize_L2(np.array([query_embedding]))
    distances, anns = index.search(np.array([query_embedding]), k=k)
    topk = [
        chunk_id
        for score, chunk_id in zip(distances.flatten(), anns.flatten())
        if score <= threshold
    ]
    chunks = doc_source.read_data().split("\n")
    topk_content = [f'{{chunk_id:"{i}";content:"{chunks[i]}"}}' for i in topk]
    logger.info("Top K contents: " + "\n  ".join(topk_content))

    context = "".join(topk_content)
    ai_answer = ai.ask1(get_prompt(context, query))
    answer, sources = parse_ai_answer(ai_answer)
    # answer_sources = [
    #     (answer, chunks[chunk_id])
    #     for chunk_id, answer in parse_ai_answer(ai_answer)
    #     if chunk_id < len(chunks)
    # ]

    return answer, [chunks[chunk_id] for chunk_id in sources]
