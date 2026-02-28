"""Tests for contract Pydantic schemas — grade calculation."""

import uuid
from datetime import UTC, datetime

from nile.schemas.contract import NileScoreResponse


class TestNileScoreResponseGrade:
    def _make_score(self, total: float) -> NileScoreResponse:
        return NileScoreResponse(
            id=uuid.uuid4(),
            contract_id=uuid.uuid4(),
            total_score=total,
            name_score=total,
            image_score=total,
            likeness_score=total,
            essence_score=total,
            score_details={},
            trigger_type="api",
            computed_at=datetime.now(UTC),
        )

    def test_grade_a_plus(self):
        assert self._make_score(95).grade == "A+"

    def test_grade_a_plus_boundary(self):
        assert self._make_score(90).grade == "A+"

    def test_grade_a(self):
        assert self._make_score(85).grade == "A"

    def test_grade_a_boundary(self):
        assert self._make_score(80).grade == "A"

    def test_grade_b(self):
        assert self._make_score(75).grade == "B"

    def test_grade_c(self):
        assert self._make_score(65).grade == "C"

    def test_grade_d(self):
        assert self._make_score(55).grade == "D"

    def test_grade_f(self):
        assert self._make_score(40).grade == "F"

    def test_grade_f_zero(self):
        assert self._make_score(0).grade == "F"

    def test_grade_a_plus_100(self):
        assert self._make_score(100).grade == "A+"
