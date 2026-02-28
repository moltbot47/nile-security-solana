"""Tests for person profile endpoints."""

import uuid

from nile.core.auth import create_agent_token
from nile.models.agent import Agent
from nile.models.person import Person

# --- Helpers ---


async def _create_auth_agent(db_session) -> tuple[Agent, str]:
    """Create an active agent and return (agent, jwt_token)."""
    agent = Agent(
        name=f"auth-agent-{uuid.uuid4().hex[:6]}",
        owner_id="owner-test",
        capabilities=["detect"],
        status="active",
        api_key_hash="unused",
    )
    db_session.add(agent)
    await db_session.flush()
    token = create_agent_token(str(agent.id))
    return agent, token


async def _create_person(db_session, slug: str, **kwargs) -> Person:
    """Create a person in the DB."""
    person = Person(
        display_name=kwargs.get("display_name", slug.replace("-", " ").title()),
        slug=slug,
        bio=kwargs.get("bio"),
        category=kwargs.get("category", "general"),
        tags=kwargs.get("tags", []),
        social_links=kwargs.get("social_links", {}),
    )
    db_session.add(person)
    await db_session.flush()
    return person


# --- Create ---


async def test_create_person(client, db_session):
    """POST /persons creates a new person profile."""
    _, token = await _create_auth_agent(db_session)
    response = await client.post(
        "/api/v1/persons",
        json={
            "display_name": "Test Person",
            "slug": "test-person",
            "bio": "A test bio",
            "category": "athlete",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["display_name"] == "Test Person"
    assert data["slug"] == "test-person"
    assert data["category"] == "athlete"


async def test_create_person_duplicate_slug(client, db_session):
    """Creating person with existing slug returns 409."""
    _, token = await _create_auth_agent(db_session)
    await _create_person(db_session, "dup-slug")

    response = await client.post(
        "/api/v1/persons",
        json={"display_name": "Another", "slug": "dup-slug"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 409


async def test_create_person_invalid_slug(client, db_session):
    """Slug with invalid chars is rejected by validation."""
    _, token = await _create_auth_agent(db_session)
    response = await client.post(
        "/api/v1/persons",
        json={"display_name": "Bad Slug", "slug": "Bad Slug!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


# --- List ---


async def test_list_persons_empty(client):
    """GET /persons returns empty list when no persons exist."""
    response = await client.get("/api/v1/persons")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_persons_with_data(client, db_session):
    """GET /persons returns persons after creation."""
    await _create_person(db_session, "list-person-1")
    await _create_person(db_session, "list-person-2")

    response = await client.get("/api/v1/persons")
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_persons_filter_category(client, db_session):
    """GET /persons?category=athlete filters by category."""
    await _create_person(db_session, "athlete-1", category="athlete")
    await _create_person(db_session, "musician-1", category="musician")

    response = await client.get("/api/v1/persons?category=athlete")
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "athlete"


async def test_list_persons_search(client, db_session):
    """GET /persons?search=keyword filters by display_name."""
    await _create_person(db_session, "alpha-person", display_name="Alpha Star")
    await _create_person(db_session, "beta-person", display_name="Beta Ray")

    response = await client.get("/api/v1/persons?search=Alpha")
    data = response.json()
    assert len(data) == 1
    assert data[0]["display_name"] == "Alpha Star"


# --- Get by ID ---


async def test_get_person_by_id(client, db_session):
    """GET /persons/{id} returns the correct person."""
    person = await _create_person(db_session, "get-me")

    response = await client.get(f"/api/v1/persons/{person.id}")
    assert response.status_code == 200
    assert response.json()["slug"] == "get-me"


async def test_get_person_not_found(client):
    """GET /persons/{id} returns 404 for non-existent person."""
    fake_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/persons/{fake_id}")
    assert response.status_code == 404


# --- Update ---


async def test_update_person(client, db_session):
    """PATCH /persons/{id} updates person fields."""
    _, token = await _create_auth_agent(db_session)
    person = await _create_person(db_session, "update-me")

    response = await client.patch(
        f"/api/v1/persons/{person.id}",
        json={"bio": "Updated bio", "category": "creator"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["bio"] == "Updated bio"
    assert data["category"] == "creator"


async def test_update_person_not_found(client, db_session):
    """PATCH /persons/{id} returns 404 for non-existent person."""
    _, token = await _create_auth_agent(db_session)
    fake_id = str(uuid.uuid4())
    response = await client.patch(
        f"/api/v1/persons/{fake_id}",
        json={"bio": "nope"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


# --- Valuation History ---


async def test_valuation_history_empty(client, db_session):
    """GET /persons/{id}/valuation-history returns empty list when none exist."""
    person = await _create_person(db_session, "val-empty")
    response = await client.get(f"/api/v1/persons/{person.id}/valuation-history")
    assert response.status_code == 200
    assert response.json() == []


# --- Oracle Events ---


async def test_oracle_events_empty(client, db_session):
    """GET /persons/{id}/oracle-events returns empty list when none exist."""
    person = await _create_person(db_session, "oracle-empty")
    response = await client.get(f"/api/v1/persons/{person.id}/oracle-events")
    assert response.status_code == 200
    assert response.json() == []


# --- Categories ---


async def test_categories_returns_counts(client, db_session):
    """GET /persons/categories returns category counts."""
    await _create_person(db_session, "cat-a1", category="athlete")
    await _create_person(db_session, "cat-a2", category="athlete")
    await _create_person(db_session, "cat-m1", category="musician")

    response = await client.get("/api/v1/persons/categories")
    assert response.status_code == 200
    data = response.json()
    cats = {item["category"]: item["count"] for item in data}
    assert cats["athlete"] == 2
    assert cats["musician"] == 1
