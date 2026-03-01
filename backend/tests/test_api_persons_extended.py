"""Extended tests for persons API — trending, sort, verification filter, oracle events."""

import pytest

from nile.models.oracle_event import OracleEvent
from nile.models.person import Person
from nile.models.soul_token import SoulToken


async def _create_person_with_token(db_session, slug, volume=1000.0, **kwargs):
    """Create a person with an associated soul token."""
    person = Person(
        display_name=kwargs.get("display_name", slug.replace("-", " ").title()),
        slug=slug,
        category=kwargs.get("category", "athlete"),
        verification_level=kwargs.get("verification_level", "unverified"),
    )
    db_session.add(person)
    await db_session.flush()

    token = SoulToken(
        person_id=person.id,
        name=f"{slug} Token",
        symbol=slug[:3].upper(),
        phase="bonding",
        chain="solana",
        current_price_sol=0.01,
        current_price_usd=2.50,
        market_cap_usd=10000.0,
        volume_24h_usd=volume,
        total_supply=1000000,
        reserve_balance_sol=5.0,
        graduation_threshold_sol=100.0,
    )
    db_session.add(token)
    await db_session.flush()
    return person, token


@pytest.mark.asyncio
class TestTrendingPersons:
    async def test_empty_trending(self, client, db_session):
        resp = await client.get("/api/v1/persons/trending")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_trending_ordered_by_volume(self, client, db_session):
        await _create_person_with_token(db_session, "low-vol", volume=100.0)
        await _create_person_with_token(db_session, "high-vol", volume=50000.0)

        resp = await client.get("/api/v1/persons/trending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        # Higher volume should be first
        assert data[0]["slug"] == "high-vol"


@pytest.mark.asyncio
class TestListPersonsSortVariants:
    async def test_sort_by_newest(self, client, db_session):
        p1 = Person(display_name="First", slug="first-sort", category="general")
        db_session.add(p1)
        await db_session.flush()

        p2 = Person(display_name="Second", slug="second-sort", category="general")
        db_session.add(p2)
        await db_session.flush()

        resp = await client.get("/api/v1/persons?sort=newest")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    async def test_sort_by_name(self, client, db_session):
        db_session.add(Person(display_name="Zeta", slug="zeta-sort", category="general"))
        db_session.add(Person(display_name="Alpha", slug="alpha-sort", category="general"))
        await db_session.flush()

        resp = await client.get("/api/v1/persons?sort=name")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["display_name"] == "Alpha"

    async def test_filter_verification(self, client, db_session):
        p1 = Person(
            display_name="Verified",
            slug="verified-p",
            category="general",
            verification_level="verified",
        )
        p2 = Person(
            display_name="Unverified",
            slug="unverified-p",
            category="general",
            verification_level="unverified",
        )
        db_session.add_all([p1, p2])
        await db_session.flush()

        resp = await client.get("/api/v1/persons?verification=verified")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Verified"


@pytest.mark.asyncio
class TestOracleEventsWithFilter:
    async def test_oracle_events_with_data(self, client, db_session):
        person = Person(display_name="Event Person", slug="event-p", category="general")
        db_session.add(person)
        await db_session.flush()

        event = OracleEvent(
            person_id=person.id,
            event_type="sports_win",
            source="espn",
            headline="Won game",
            impact_score=50,
            confidence=0.8,
            status="confirmed",
            confirmations=2,
            rejections=0,
        )
        db_session.add(event)
        await db_session.flush()

        resp = await client.get(f"/api/v1/persons/{person.id}/oracle-events")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "confirmed"

    async def test_oracle_events_filter_status(self, client, db_session):
        person = Person(display_name="Filter Person", slug="filter-p", category="general")
        db_session.add(person)
        await db_session.flush()

        for status in ("pending", "confirmed"):
            db_session.add(
                OracleEvent(
                    person_id=person.id,
                    event_type="news",
                    source="reuters",
                    headline=f"Event {status}",
                    impact_score=30,
                    confidence=0.7,
                    status=status,
                )
            )
        await db_session.flush()

        resp = await client.get(f"/api/v1/persons/{person.id}/oracle-events?status=pending")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "pending"
