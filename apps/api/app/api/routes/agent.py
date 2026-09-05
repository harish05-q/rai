from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.agents.exceptions import AgentError
from app.agents.orchestrator import AgentOrchestrator
from app.agents.schemas import (
    AgentCaseResponse,
    AgentStatus,
    AgentSummary,
    AIRecoveryDecision,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    PaginatedAgentActivity,
)
from app.api.deps import get_db

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def _orchestrator(db: Session = Depends(get_db)) -> AgentOrchestrator:
    return AgentOrchestrator(db)


def _http_error(exc: AgentError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


@router.get("/status", response_model=AgentStatus)
def agent_status(orchestrator: AgentOrchestrator = Depends(_orchestrator)) -> AgentStatus:
    return orchestrator.status()


@router.get("/summary", response_model=AgentSummary)
def agent_summary(orchestrator: AgentOrchestrator = Depends(_orchestrator)) -> AgentSummary:
    return orchestrator.summary()


@router.get("/activity", response_model=PaginatedAgentActivity)
def agent_activity(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    orchestrator: AgentOrchestrator = Depends(_orchestrator),
) -> PaginatedAgentActivity:
    items, total = orchestrator.activity(limit=limit, offset=offset)
    return PaginatedAgentActivity(items=items, total=total, limit=limit, offset=offset)


@router.get("/cases/{case_id}", response_model=AgentCaseResponse)
def get_case_analysis(
    case_id: UUID,
    orchestrator: AgentOrchestrator = Depends(_orchestrator),
) -> AgentCaseResponse:
    try:
        return orchestrator.get_case_analysis(case_id)
    except AgentError as exc:
        raise _http_error(exc) from exc


@router.post("/analyze/{case_id}", response_model=AIRecoveryDecision)
def analyze_case(
    case_id: UUID,
    orchestrator: AgentOrchestrator = Depends(_orchestrator),
) -> AIRecoveryDecision:
    try:
        return orchestrator.analyze_case(case_id, reuse_recent=False)
    except AgentError as exc:
        raise _http_error(exc) from exc


@router.post("/analyze", response_model=BatchAnalyzeResponse)
def analyze_batch(
    body: BatchAnalyzeRequest | None = None,
    orchestrator: AgentOrchestrator = Depends(_orchestrator),
) -> BatchAnalyzeResponse:
    request = body or BatchAnalyzeRequest()
    try:
        return orchestrator.analyze_batch(
            case_ids=request.case_ids,
            limit=request.limit,
            skip_existing=request.skip_existing,
        )
    except AgentError as exc:
        raise _http_error(exc) from exc
