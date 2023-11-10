import os
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from typing import Protocol
import numpy.typing as npt
import numpy as np
import config



class EmbeddingMaker(Protocol):
    def encode(self, text: str) -> npt.NDArray[np.float32]:
        ...


class AI:
    def __init__(self) -> None:
        self.client: OpenAI = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.embedder: EmbeddingMaker = SentenceTransformer(config.model_name)
      
    def encode(self, text: str) -> npt.NDArray[np.float32]:
        return self.embedder.encode(text)

    def ask1(self, prompt: str) -> str:
        messages = [
            {"role": "system", "content": "You are a document scanner."},
            {"role": "user", "content": prompt},
        ]

        chatgpt = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.3,
            n=1,
        )
        results = chatgpt.choices[0].message.content
        return results or ""
