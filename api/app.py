import hashlib
from typing import List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Header, BackgroundTasks
from pydantic import BaseModel
from uuid import uuid4
import calendar
import time
import os
import logging
from config import db_path, data_root_path, data_file_name, index_file_name
from . import models, utils
from .ai import AI

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)



ai = AI()
app = FastAPI()


# Define Pydantic models for the API
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    sourceId: str
    messages: List[Message]


class ChatResponse(BaseModel):
    content: str


class AddFileResponse(BaseModel):
    sourceId: str


class DeleteRequest(BaseModel):
    sources: List[str]


class DeleteResponse(BaseModel):
    detail: str


@app.post("/v1/sources/add-file", response_model=AddFileResponse)
async def add_pdf(
    background_task: BackgroundTasks,
    file: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
):
    if x_api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not file.filename or not file.content_type or not file.size:
        raise HTTPException(
            status_code=400, detail="Missing file data (filename, content type, or size"
        )

    data = await file.read()
    doc_id = "ch_" + hashlib.md5(data).hexdigest()
    file_document = models.Doc(
        doc_name=file.filename,
        doc_type=file.content_type,
        uid=int(str(uuid4())[:5], base=16),
        file_size=file.size,
        doc_id=doc_id,
        create_at=calendar.timegm(time.gmtime()),
        update_at=calendar.timegm(time.gmtime()),
    )
    try:
        file_document.save_db(db_path)
    except models.DocumentExistsExcpetion as e:
        # Log the message that the document exists as a warning and ignore the error
        logger.warning(str(e))
        doc = models.Doc.get_by_doc_id(db_path, doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"PDF with the same doc_id {doc_id} not found")
        if doc.state == models.DocumentState.INDEX_BUILT:
            return AddFileResponse(sourceId=doc_id)
        else:
            background_task.add_task(file_task, doc_id, file.filename, data)
    else:
        background_task.add_task(file_task, doc_id, file.filename, data)
    return AddFileResponse(sourceId=doc_id)


def file_task(doc_id: str, doc_name: str, data: bytes):
    if not models.Doc.exists_with_doc_id(db_path, doc_id):
        return

    doc_source = models.DocSource(
        doc_path=data_root_path / doc_id,
        file_name=doc_name,
    )
    doc_source.save_doc(data)
    models.Doc.update_state_with_doc_id(db_path, doc_id, models.DocumentState.UPLOADED)

    chunks = utils.process_doc(doc_source, data)
    models.Doc.update_state_with_doc_id(db_path, doc_id, models.DocumentState.PROCESSED)

    utils.create_store(doc_source, ai, chunks)
    models.Doc.update_state_with_doc_id(
        db_path, doc_id, models.DocumentState.INDEX_BUILT
    )


@app.post("/v1/sources/delete", response_model=DeleteResponse)
async def delete_pdf(
    delete_request: DeleteRequest, x_api_key: Optional[str] = Header(None)
):
    if x_api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    for source_id in delete_request.sources:
        if models.Doc.exists_with_doc_id(db_path, source_id):
            models.Doc.delete_with_doc_id(db_path, source_id)

    return DeleteResponse(detail="success")


@app.post("/v1/chats/message", response_model=ChatResponse)
async def chat_with_pdf(
    chat_request: ChatRequest, x_api_key: Optional[str] = Header(None)
):
    if x_api_key != os.environ.get("API_KEY"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not models.Doc.exists_with_doc_id(db_path, chat_request.sourceId):
        raise HTTPException(status_code=404, detail="PDF not found in DB")

    doc_id = chat_request.sourceId

    doc = models.Doc.get_by_doc_id(db_path, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="PDF not found")
    if doc.state != models.DocumentState.INDEX_BUILT:
        raise HTTPException(
            status_code=400,
            detail=f"PDF with doc_id {doc_id} has not finished indexing",
        )
    doc_source = models.DocSource(
        doc_path=data_root_path / doc_id,
        file_name=doc.doc_name,
    )

    if len(chat_request.messages) == 0:
        raise HTTPException(status_code=400, detail="No messages provided")

    try: 
        answer_sources = utils.query_item(doc_source, ai, chat_request.messages[-1].content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    else:
        if len(answer_sources) == 0:
            raise HTTPException(status_code=404, detail="No answer found")
        answer, source = answer_sources[0]
        return_content = f"{answer}\n source: {source}"
        return ChatResponse(content=return_content)
