"""Tests for oracle_consensus — event submission, voting, and revaluation."""

import uuid

import pytest
from sqlalchemy import select

from nile.models.person import Person
from nile.models.valuation_snapshot import ValuationSnapshot
from nile.services.oracle_consensus import (
    DEFAULT_REQUIRED,
    submit_oracle_report,
    vote_on_report,
)


def _make_person(db_session, **kwargs):
    """Helper to create a Person for tests."""
    defaults = dict(
        display_name="Test Person",
        slug="test-person",
        category="athlete",
        bio="Test bio",
    )
    defaults.update(kwargs)
    person = Person(**defaults)
    db_session.add(person)
    return person


@pytest.mark.asyncio
class TestSubmitOracleReport:
    async def test_creates_pending_event(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="social_viral",
            source="twitter",
            headline="Viral tweet about the athlete",
            impact_score=50,
            confidence=0.8,
        )

        assert event.status == "pending"
        assert event.confirmations == 1  # auto-confirm by submitter
        assert event.rejections == 0
        assert event.required_confirmations == DEFAULT_REQUIRED
        assert event.impact_score == 50
        assert event.confidence == pytest.approx(0.8, abs=0.01)

    async def test_records_submitter_vote(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="news_positive",
            source="espn",
            headline="Breaking news",
            impact_score=30,
        )

        assert "agent-1" in event.agent_votes
        assert event.agent_votes["agent-1"]["approve"] is True


@pytest.mark.asyncio
class TestVoteOnReport:
    async def test_approve_increments_confirmations(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="social_viral",
            source="twitter",
            headline="Test",
            impact_score=20,
        )
        assert event.confirmations == 1

        updated = await vote_on_report(
            db_session,
            agent_id="agent-2",
            event_id=event.id,
            approve=True,
        )
        assert updated.confirmations == 2

    async def test_reject_increments_rejections(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="scandal",
            source="reuters",
            headline="Test",
            impact_score=-30,
        )

        updated = await vote_on_report(
            db_session,
            agent_id="agent-2",
            event_id=event.id,
            approve=False,
        )
        assert updated.rejections == 1

    async def test_duplicate_vote_raises(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="social_viral",
            source="twitter",
            headline="Test",
            impact_score=10,
        )

        with pytest.raises(ValueError, match="already voted"):
            await vote_on_report(
                db_session,
                agent_id="agent-1",
                event_id=event.id,
                approve=True,
            )

    async def test_nonexistent_event_raises(self, db_session):
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await vote_on_report(
                db_session,
                agent_id="agent-1",
                event_id=fake_id,
                approve=True,
            )


@pytest.mark.asyncio
class TestConsensus:
    async def test_consensus_reached_confirms_event(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="sports_win",
            source="espn",
            headline="Won championship",
            impact_score=80,
        )
        # 1 confirmation from submitter, need 2 total
        assert event.status == "pending"

        updated = await vote_on_report(
            db_session,
            agent_id="agent-2",
            event_id=event.id,
            approve=True,
        )
        assert updated.status == "confirmed"

    async def test_consensus_triggers_revaluation(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="sports_win",
            source="espn",
            headline="Won championship",
            impact_score=80,
        )

        await vote_on_report(
            db_session,
            agent_id="agent-2",
            event_id=event.id,
            approve=True,
        )

        # Should have created a valuation snapshot
        result = await db_session.execute(
            select(ValuationSnapshot).where(
                ValuationSnapshot.person_id == person.id
            )
        )
        snapshot = result.scalar_one_or_none()
        assert snapshot is not None
        assert snapshot.trigger_type == "oracle_event"

    async def test_rejection_inevitable_rejects_event(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="scandal",
            source="reuters",
            headline="Test event",
            impact_score=-50,
        )

        # Two rejections → impossible to reach quorum of 2
        await vote_on_report(
            db_session, agent_id="agent-2", event_id=event.id, approve=False
        )
        updated = await vote_on_report(
            db_session, agent_id="agent-3", event_id=event.id, approve=False
        )
        assert updated.status == "rejected"

    async def test_vote_on_finalized_event_raises(self, db_session):
        person = _make_person(db_session)
        await db_session.flush()

        event = await submit_oracle_report(
            db_session,
            agent_id="agent-1",
            person_id=person.id,
            event_type="sports_win",
            source="espn",
            headline="Test",
            impact_score=50,
        )

        # Reach consensus
        await vote_on_report(
            db_session, agent_id="agent-2", event_id=event.id, approve=True
        )

        # Try to vote after finalization
        with pytest.raises(ValueError, match="already confirmed"):
            await vote_on_report(
                db_session, agent_id="agent-3", event_id=event.id, approve=True
            )
