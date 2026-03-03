"""Agent registry API — register, manage, and query ecosystem agents."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nile.core.auth import (
    create_agent_token,
    generate_api_key,
    get_current_agent,
    hash_api_key,
)
from nile.core.database import get_db
from nile.core.event_bus import publish_event
from nile.core.rate_limit import create_limiter
from nile.models.agent import Agent
from nile.models.agent_contribution import AgentContribution
from nile.schemas.soul_token import HeartbeatResponse

router = APIRouter()

# 5 registrations per minute per IP
register_limiter = create_limiter(max_requests=5, window_seconds=60)
# 60 heartbeats per minute per IP (1/sec is normal)
heartbeat_limiter = create_limiter(max_requests=60, window_seconds=60)


# --- Schemas ---


class AgentRegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(None, max_length=2000)
    version: str = Field("0.1.0", max_length=32)
    owner_id: str = Field(..., min_length=1, max_length=128)
    capabilities: list[str] = Field(default_factory=list)
    config_schema: dict = Field(default_factory=dict)
    api_endpoint: str | None = Field(None, max_length=512)
    docker_image: str | None = Field(None, max_length=256)


class AgentRegisterResponse(BaseModel):
    id: str
    name: str
    api_key: str
    jwt_token: str
    status: str


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    version: str
    owner_id: str
    capabilities: list
    status: str
    nile_score_total: float
    nile_score_name: float
    nile_score_image: float
    nile_score_likeness: float
    nile_score_essence: float
    total_points: int
    total_contributions: int
    is_online: bool
    created_at: str


class AgentUpdateRequest(BaseModel):
    description: str | None = Field(None, max_length=2000)
    version: str | None = Field(None, max_length=32)
    capabilities: list[str] | None = None
    config_schema: dict | None = None
    api_endpoint: str | None = Field(None, max_length=512)
    docker_image: str | None = Field(None, max_length=256)


class ContributionResponse(BaseModel):
    id: str
    contribution_type: str
    severity_found: str | None
    verified: bool
    points_awarded: int
    summary: str | None
    created_at: str


class LeaderboardEntry(BaseModel):
    id: str
    name: str
    total_points: int
    total_contributions: int
    nile_score_total: float
    capabilities: list
    is_online: bool


# --- Endpoints ---


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(
    req: AgentRegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    """Register a new agent and receive API key + JWT token."""
    await register_limiter.check(request)
    existing = await db.execute(select(Agent).where(Agent.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Agent name already taken")

    api_key = generate_api_key()
    agent = Agent(
        name=req.name,
        description=req.description,
        version=req.version,
        owner_id=req.owner_id,
        capabilities=req.capabilities,
        config_schema=req.config_schema,
        api_endpoint=req.api_endpoint,
        docker_image=req.docker_image,
        api_key_hash=hash_api_key(api_key),
        status="active",
    )
    db.add(agent)
    await db.flush()

    jwt_token = create_agent_token(str(agent.id))

    await publish_event(
        event_type="agent.joined",
        actor_id=str(agent.id),
        metadata={"name": agent.name, "capabilities": agent.capabilities},
        db=db,
    )

    await db.commit()

    return AgentRegisterResponse(
        id=str(agent.id),
        name=agent.name,
        api_key=api_key,
        jwt_token=jwt_token,
        status=agent.status,
    )


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    status: str | None = Query(None, pattern=r"^(active|inactive|suspended)$"),
    capability: str | None = Query(None, pattern=r"^(detect|patch|exploit)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List agents, optionally filtered by status or capability."""
    query = select(Agent)
    if status:
        query = query.where(Agent.status == status)
    query = query.order_by(Agent.total_points.desc()).limit(limit)

    result = await db.execute(query)
    agents = result.scalars().all()

    # Filter by capability in Python (JSONB array contains)
    if capability:
        agents = [a for a in agents if capability in (a.capabilities or [])]

    return [
        AgentResponse(
            id=str(a.id),
            name=a.name,
            description=a.description,
            version=a.version,
            owner_id=a.owner_id,
            capabilities=a.capabilities or [],
            status=a.status,
            nile_score_total=float(a.nile_score_total),
            nile_score_name=float(a.nile_score_name),
            nile_score_image=float(a.nile_score_image),
            nile_score_likeness=float(a.nile_score_likeness),
            nile_score_essence=float(a.nile_score_essence),
            total_points=a.total_points,
            total_contributions=a.total_contributions,
            is_online=a.is_online,
            created_at=a.created_at.isoformat() if a.created_at else "",
        )
        for a in agents
    ]


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    capability: str | None = None,
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Agent leaderboard ranked by total points."""
    query = (
        select(Agent)
        .where(Agent.status == "active")
        .order_by(Agent.total_points.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    agents = result.scalars().all()

    if capability:
        agents = [a for a in agents if capability in (a.capabilities or [])]

    return [
        LeaderboardEntry(
            id=str(a.id),
            name=a.name,
            total_points=a.total_points,
            total_contributions=a.total_contributions,
            nile_score_total=float(a.nile_score_total),
            capabilities=a.capabilities or [],
            is_online=a.is_online,
        )
        for a in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get agent details by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        version=agent.version,
        owner_id=agent.owner_id,
        capabilities=agent.capabilities or [],
        status=agent.status,
        nile_score_total=float(agent.nile_score_total),
        nile_score_name=float(agent.nile_score_name),
        nile_score_image=float(agent.nile_score_image),
        nile_score_likeness=float(agent.nile_score_likeness),
        nile_score_essence=float(agent.nile_score_essence),
        total_points=agent.total_points,
        total_contributions=agent.total_contributions,
        is_online=agent.is_online,
        created_at=agent.created_at.isoformat() if agent.created_at else "",
    )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: uuid.UUID,
    req: AgentUpdateRequest,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    """Update agent profile (own agent only)."""
    if str(current_agent.id) != str(agent_id):
        raise HTTPException(status_code=403, detail="Can only update your own agent")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Agent not found")

    for field_name, value in req.model_dump(exclude_none=True).items():
        setattr(agent, field_name, value)

    await db.commit()
    return await get_agent(agent_id, db)


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    agent_id: uuid.UUID,
    request: Request,
    current_agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> HeartbeatResponse:
    """Report agent liveness. Expected every 30s."""
    await heartbeat_limiter.check(request)
    if str(current_agent.id) != str(agent_id):
        raise HTTPException(status_code=403, detail="Can only heartbeat your own agent")

    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:  # pragma: no cover
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.is_online = True
    agent.last_heartbeat = datetime.now(UTC)  # type: ignore[assignment]
    await db.commit()

    return HeartbeatResponse(status="ok", agent_id=str(agent_id))


@router.get("/{agent_id}/contributions", response_model=list[ContributionResponse])
async def agent_contributions(
    agent_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get contribution history for an agent."""
    result = await db.execute(
        select(AgentContribution)
        .where(AgentContribution.agent_id == agent_id)
        .order_by(AgentContribution.created_at.desc())
        .limit(limit)
    )
    contributions = result.scalars().all()

    return [
        ContributionResponse(
            id=str(c.id),
            contribution_type=c.contribution_type,
            severity_found=c.severity_found,
            verified=c.verified,
            points_awarded=c.points_awarded,
            summary=c.summary,
            created_at=c.created_at.isoformat() if c.created_at else "",
        )
        for c in contributions
    ]
