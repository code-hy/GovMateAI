import json
import time
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse

from backend.api.deps import get_orchestrator
from backend.core.database import create_session, get_session_messages, list_sessions, update_session_timestamp
from backend.models.schemas import ChatRequest, ChatResponse
from backend.rag.judge import run_builtin_judge
from backend.rag.metrics import save_llm_call, update_feedback
from backend.rag.orchestrator import RAGOrchestrator

router = APIRouter()


@router.post("/api/v1/feedback")
async def submit_feedback(request: Request):
    form = await request.form()
    call_id = form.get("call_id")
    feedback_val = form.get("feedback")
    if call_id and feedback_val:
        update_feedback(call_id, int(feedback_val))
    return StreamingResponse("", media_type="text/html")


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_json(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    orchestrator: RAGOrchestrator = Depends(get_orchestrator),
):
    call_id = str(uuid.uuid4())
    if not req.session_id:
        req.session_id = str(uuid.uuid4())

    start = time.time()
    result = orchestrator.process_query(req.question, req.session_id)
    latency = time.time() - start

    prompt_tokens = len(req.question) + 3000
    completion_tokens = int(len(result["answer"].split()) * 1.3)

    background_tasks.add_task(
        save_llm_call,
        call_id=call_id,
        session_id=req.session_id,
        question=req.question,
        answer=result["answer"],
        context_docs=result["source_docs"],
        latency=latency,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    background_tasks.add_task(
        run_builtin_judge, call_id, req.question, result["answer"]
    )

    return ChatResponse(answer=result["answer"], sources=result["sources"])


@router.post("/api/v1/chat/htmx")
async def chat_htmx(
    request: Request,
    background_tasks: BackgroundTasks,
    orchestrator: RAGOrchestrator = Depends(get_orchestrator),
):
    form = await request.form()
    question = form.get("question")
    session_id = form.get("session_id", str(uuid.uuid4()))
    call_id = str(uuid.uuid4())

    async def generate():
        start_time = time.time()

        yield f'<div class="flex justify-end mb-4"><div class="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[80%] shadow">{question}</div></div>'
        yield '<div class="flex justify-start mb-2"><div class="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-sm prose prose-sm max-w-none">'

        full_text = ""

        for token in orchestrator.process_query_stream(
            question, session_id
        ):
            if isinstance(token, str) and token.startswith("__SOURCES__"):
                yield "</div></div>"
                sources = json.loads(token.replace("__SOURCES__", ""))
                if sources:
                    yield f'<div class="ml-4 mt-1 text-xs text-gray-500 border-l-2 border-gray-200 pl-2 space-y-1">'
                    for s in sources:
                        yield f'<a href="{s["url"]}" target="_blank" class="block hover:text-blue-600">【{s["index"]}】 {s["title"]} ({s["agency"]})</a>'
                    yield "</div>"

                yield f'<div class="flex gap-3 mt-3 ml-4" id="fb-{call_id}">'
                yield f'<span class="text-xs text-gray-400 mt-1">Helpful?</span>'
                yield f'<button class="text-sm hover:text-green-600" hx-post="/api/v1/feedback" hx-vals=\'{{"call_id":"{call_id}","feedback":"1"}}\' hx-target="#fb-{call_id}" hx-swap="outerHTML">👍</button>'
                yield f'<button class="text-sm hover:text-red-600" hx-post="/api/v1/feedback" hx-vals=\'{{"call_id":"{call_id}","feedback":"-1"}}\' hx-target="#fb-{call_id}" hx-swap="outerHTML">👎</button>'
                yield "</div>"
            else:
                full_text += token
                yield token

        if not full_text:
            yield "</div></div>"

        latency = time.time() - start_time
        prompt_tokens = len(question) + 3000
        completion_tokens = int(len(full_text.split()) * 1.3)
        rewritten = orchestrator.retriever.retrieve(question)[:5]
        top_docs = orchestrator.reranker.rerank(question, rewritten, 5)

        create_session(session_id, question[:80])

        background_tasks.add_task(
            save_llm_call,
            call_id=call_id,
            session_id=session_id,
            question=question,
            answer=full_text,
            context_docs=top_docs,
            latency=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        background_tasks.add_task(
            run_builtin_judge, call_id, question, full_text
        )
        background_tasks.add_task(update_session_timestamp, session_id)

    return StreamingResponse(generate(), media_type="text/html")


@router.get("/api/v1/sessions", response_class=HTMLResponse)
async def list_chat_sessions():
    sessions = list_sessions()
    items = ""
    for s in sessions:
        sid = s["session_id"]
        title = s["title"]
        items += f'<a href="#" class="session-item block px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg truncate" data-session="{sid}">{title}</a>'
    return HTMLResponse(items)


@router.get("/api/v1/sessions/{session_id}", response_class=HTMLResponse)
async def load_session(session_id: str):
    messages = get_session_messages(session_id)
    html = ""
    for m in messages:
        html += f'<div class="flex justify-end mb-4"><div class="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-[80%] shadow">{m["question"]}</div></div>'
        html += f'<div class="flex justify-start mb-2"><div class="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-3 max-w-[80%] shadow-sm prose prose-sm max-w-none"><p>{m["answer"]}</p></div></div>'
    return HTMLResponse(html)
