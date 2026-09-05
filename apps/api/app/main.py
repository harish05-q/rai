from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import actions, agent, analytics, approvals, audit, demo, health, outcomes, payments, policies, recovery
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="R.AI API", version="0.4.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(payments.router)
app.include_router(recovery.router)
app.include_router(agent.router)
app.include_router(policies.router)
app.include_router(actions.router)
app.include_router(approvals.router)
app.include_router(audit.router)
app.include_router(analytics.router)
app.include_router(outcomes.router)
app.include_router(demo.router)
