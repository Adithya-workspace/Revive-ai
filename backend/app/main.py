from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import detection, scoring, diagnosis, strategy, policy, actions

app = FastAPI(
    title="REVIVE AI",
    description="Autonomous Revenue Recovery Intelligence — backend API",
    version="0.1.0",
)

# Allow the Next.js frontend (running on localhost:3000) to call this API.
# We'll tighten this once we're closer to deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(detection.router)
app.include_router(scoring.router)
app.include_router(diagnosis.router)
app.include_router(strategy.router)
app.include_router(policy.router)
app.include_router(actions.router)
@app.get("/")
def root():
    return {"status": "ok", "service": "revive-ai-backend"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
