"""
Proposal Assistant Agent — FastAPI server
Run with: uvicorn main:app --reload
"""

import json
import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request

import agent
from pdf_utils import extract_text_from_pdf_bytes, truncate_rfp

app = FastAPI(title="Proposal Assistant Agent", version="0.1.0")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/analyze")
async def analyze(
    rfp_text: Optional[str] = Form(None),
    rfp_file: Optional[UploadFile] = File(None),
):
    """
    Step 1 + 2: Extract requirements from RFP and match to capabilities.
    Returns JSON with requirements + matched capabilities.
    Accepts either a text paste (rfp_text) or a PDF/txt file upload (rfp_file).
    """
    # --- Get raw text ---
    if rfp_file and rfp_file.filename:
        contents = await rfp_file.read()
        if rfp_file.filename.lower().endswith(".pdf"):
            try:
                raw_text = extract_text_from_pdf_bytes(contents)
            except Exception as e:
                raise HTTPException(status_code=422, detail=f"PDF extraction failed: {e}")
        else:
            raw_text = contents.decode("utf-8", errors="replace")
    elif rfp_text and rfp_text.strip():
        raw_text = rfp_text
    else:
        raise HTTPException(status_code=422, detail="Provide either rfp_text or rfp_file.")

    text, was_truncated = truncate_rfp(raw_text)

    # --- Step 1: Extract requirements ---
    try:
        requirements = agent.extract_requirements(text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Requirement extraction failed: {e}")

    if "parse_error" in requirements:
        raise HTTPException(
            status_code=500,
            detail=f"Could not parse requirements JSON: {requirements['parse_error'][:200]}",
        )

    # --- Step 2: Match capabilities ---
    try:
        matched = agent.match_capabilities(requirements)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Capability matching failed: {e}")

    return {
        "requirements": requirements,
        "matched": matched,
        "truncated": was_truncated,
        "char_count": len(text),
    }


@app.post("/api/draft")
async def draft(request: Request):
    """
    Step 3: Stream-generate the full proposal draft.
    Accepts JSON body: { "requirements": {...}, "matched": {...} }
    Returns SSE stream of text chunks.
    """
    body = await request.json()
    requirements = body.get("requirements")
    matched = body.get("matched")

    if not requirements or not matched:
        raise HTTPException(
            status_code=422, detail="Body must include 'requirements' and 'matched' keys."
        )

    async def event_stream():
        try:
            async for chunk in agent.stream_draft(requirements, matched):
                # SSE format
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
