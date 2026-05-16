from __future__ import annotations

import time

from fastapi import FastAPI, HTTPException

from app.agents.baseline_agent import run_baseline
from app.agents.crew_agent import run_crew
from app.schemas import AskRequest, AskResponse
from app.tools.finance_tools import dataset_summary


app = FastAPI(
    title="Lesson 11 Personal Finance Crew",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "personal-finance-crew",
    }


@app.get("/dataset-summary")
def get_dataset_summary() -> dict:
    return dataset_summary()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    started = time.perf_counter()

    try:
        if request.architecture == "baseline":
            response = run_baseline(
                question=request.question,
                session_id=request.session_id,
            )
        elif request.architecture == "crew":
            response = run_crew(
                question=request.question,
                session_id=request.session_id,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="architecture must be 'baseline' or 'crew'",
            )

        response.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return response

    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {error}",
        ) from error