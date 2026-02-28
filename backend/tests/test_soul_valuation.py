"""Tests for soul_valuation — NILE 4-dimension scoring for human NIL value."""

import pytest

from nile.services.soul_valuation import (
    BASE_VALUES,
    CATEGORY_MULTIPLIERS,
    PersonEssenceInputs,
    PersonImageInputs,
    PersonLikenessInputs,
    PersonNameInputs,
    compute_person_essence_score,
    compute_person_image_score,
    compute_person_likeness_score,
    compute_person_name_score,
    compute_person_valuation,
)

# ── Name dimension ──────────────────────────────────────────────


class TestNameScore:
    def test_all_zeros(self):
        score, details = compute_person_name_score(PersonNameInputs())
        assert score == 0.0
        assert details["verification"] == 0

    def test_verified_level(self):
        score, _ = compute_person_name_score(
            PersonNameInputs(verification_level="verified")
        )
        assert score >= 20.0

    def test_premium_level(self):
        score, _ = compute_person_name_score(
            PersonNameInputs(verification_level="premium")
        )
        assert score >= 30.0

    def test_kyc_bonus(self):
        without_kyc, _ = compute_person_name_score(PersonNameInputs())
        with_kyc, details = compute_person_name_score(
            PersonNameInputs(kyc_completed=True)
        )
        assert details["kyc_bonus"] == 10.0
        assert with_kyc - without_kyc == 10.0

    def test_social_accounts_capped(self):
        _, details = compute_person_name_score(
            PersonNameInputs(social_account_count=100)
        )
        assert details["social_presence"] == 15.0

    def test_follower_log_scale(self):
        s1, _ = compute_person_name_score(PersonNameInputs(follower_count=100))
        s2, _ = compute_person_name_score(PersonNameInputs(follower_count=1_000_000))
        assert s2 > s1

    def test_follower_capped_at_25(self):
        _, details = compute_person_name_score(
            PersonNameInputs(follower_count=10**12)
        )
        assert details["follower_reach"] <= 25.0

    def test_domain_authority_capped(self):
        _, details = compute_person_name_score(
            PersonNameInputs(domain_authority=50.0)
        )
        assert details["domain_authority"] == 20.0

    def test_max_score_is_100(self):
        score, _ = compute_person_name_score(
            PersonNameInputs(
                verification_level="premium",
                social_account_count=10,
                follower_count=10**9,
                domain_authority=20.0,
                kyc_completed=True,
            )
        )
        assert score <= 100.0


# ── Image dimension ─────────────────────────────────────────────


class TestImageScore:
    def test_neutral_baseline(self):
        score, _details = compute_person_image_score(PersonImageInputs())
        assert score == pytest.approx(37.5, abs=0.1)

    def test_perfect_sentiment(self):
        score, _ = compute_person_image_score(
            PersonImageInputs(avg_sentiment=1.0)
        )
        assert score >= 50.0

    def test_negative_sentiment(self):
        score, _ = compute_person_image_score(
            PersonImageInputs(avg_sentiment=0.0)
        )
        assert score < 25.0

    def test_positive_events_boost(self):
        _score, details = compute_person_image_score(
            PersonImageInputs(positive_events=10, negative_events=0)
        )
        assert details["event_impact"] == 25.0

    def test_media_mentions_capped(self):
        _, details = compute_person_image_score(
            PersonImageInputs(media_mention_count=100)
        )
        assert details["media_coverage"] == 15.0

    def test_engagement_capped(self):
        _, details = compute_person_image_score(
            PersonImageInputs(engagement_rate=200)
        )
        assert details["engagement"] == 10.0


# ── Likeness dimension ──────────────────────────────────────────


class TestLikenessScore:
    def test_defaults_give_neutral_score(self):
        score, _details = compute_person_likeness_score(PersonLikenessInputs())
        assert score == pytest.approx(50.0, abs=0.1)

    def test_top_rank_gives_high_score(self):
        score, _ = compute_person_likeness_score(
            PersonLikenessInputs(category_rank_percentile=100.0)
        )
        assert score >= 50.0

    def test_market_cap_ratio(self):
        _, details = compute_person_likeness_score(
            PersonLikenessInputs(
                own_market_cap=2_000_000,
                peer_avg_market_cap=1_000_000,
            )
        )
        assert details["peer_comparison"] == 30.0

    def test_comparables_capped(self):
        _, details = compute_person_likeness_score(
            PersonLikenessInputs(comparable_token_prices=[1.0] * 20)
        )
        assert details["comparable_depth"] == 20.0


# ── Essence dimension ───────────────────────────────────────────


class TestEssenceScore:
    def test_all_zeros(self):
        score, _ = compute_person_essence_score(PersonEssenceInputs())
        assert score == pytest.approx(10.0, abs=0.1)

    def test_career_years_capped(self):
        _, details = compute_person_essence_score(
            PersonEssenceInputs(career_years=20)
        )
        assert details["career_maturity"] == 20.0

    def test_rising_trajectory(self):
        _, details = compute_person_essence_score(
            PersonEssenceInputs(trajectory_slope=1.0)
        )
        assert details["trajectory"] == 20.0

    def test_declining_trajectory(self):
        _, details = compute_person_essence_score(
            PersonEssenceInputs(trajectory_slope=-1.0)
        )
        assert details["trajectory"] == 0.0

    def test_earning_potential_log(self):
        _, d1 = compute_person_essence_score(
            PersonEssenceInputs(annual_earning_estimate=100_000)
        )
        _, d2 = compute_person_essence_score(
            PersonEssenceInputs(annual_earning_estimate=10_000_000)
        )
        assert d2["earning_potential"] > d1["earning_potential"]


# ── Full valuation pipeline ─────────────────────────────────────


class TestFullValuation:
    def test_default_inputs_produce_valid_result(self):
        result = compute_person_valuation(
            PersonNameInputs(),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(),
        )
        assert 0 <= result.total_score <= 100
        assert result.grade in ("A+", "A", "B", "C", "D", "F")
        assert result.fair_value_usd >= 0
        assert "name" in result.details

    def test_high_inputs_produce_high_grade(self):
        result = compute_person_valuation(
            PersonNameInputs(
                verification_level="premium",
                social_account_count=5,
                follower_count=1_000_000,
                domain_authority=20.0,
                kyc_completed=True,
            ),
            PersonImageInputs(
                positive_events=20,
                avg_sentiment=0.9,
                media_mention_count=10,
                engagement_rate=80,
            ),
            PersonLikenessInputs(category_rank_percentile=95),
            PersonEssenceInputs(
                career_years=15,
                achievement_count=5,
                endorsement_count=5,
                annual_earning_estimate=5_000_000,
                trajectory_slope=0.8,
            ),
        )
        assert result.grade in ("A+", "A")
        assert result.total_score >= 80

    def test_category_multiplier_affects_fair_value(self):
        general = compute_person_valuation(
            PersonNameInputs(verification_level="verified"),
            PersonImageInputs(),
            PersonLikenessInputs(category="general"),
            PersonEssenceInputs(),
        )
        athlete = compute_person_valuation(
            PersonNameInputs(verification_level="verified"),
            PersonImageInputs(),
            PersonLikenessInputs(category="athlete"),
            PersonEssenceInputs(),
        )
        assert athlete.fair_value_usd > general.fair_value_usd

    def test_verification_level_affects_base_value(self):
        unverified = compute_person_valuation(
            PersonNameInputs(verification_level="unverified"),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(),
        )
        premium = compute_person_valuation(
            PersonNameInputs(verification_level="premium"),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(),
        )
        assert premium.fair_value_usd > unverified.fair_value_usd

    def test_custom_weights(self):
        result = compute_person_valuation(
            PersonNameInputs(verification_level="premium", kyc_completed=True),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(),
            weights={"name": 1.0, "image": 0.0, "likeness": 0.0, "essence": 0.0},
        )
        assert result.total_score == result.name_score

    def test_negative_trajectory_reduces_fair_value(self):
        rising = compute_person_valuation(
            PersonNameInputs(),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(trajectory_slope=1.0),
        )
        declining = compute_person_valuation(
            PersonNameInputs(),
            PersonImageInputs(),
            PersonLikenessInputs(),
            PersonEssenceInputs(trajectory_slope=-1.0),
        )
        assert rising.fair_value_usd > declining.fair_value_usd

    def test_grade_boundaries(self):
        from nile.services.nile_scorer import GRADE_MAP

        for threshold, _grade in GRADE_MAP:
            result = compute_person_valuation(
                PersonNameInputs(verification_level="premium", kyc_completed=True),
                PersonImageInputs(avg_sentiment=threshold / 100),
                PersonLikenessInputs(category_rank_percentile=threshold),
                PersonEssenceInputs(career_years=10, trajectory_slope=0.5),
            )
            assert result.grade in ("A+", "A", "B", "C", "D", "F")

    def test_category_multipliers_dict(self):
        assert CATEGORY_MULTIPLIERS["athlete"] == 2.5
        assert CATEGORY_MULTIPLIERS["general"] == 1.0

    def test_base_values_dict(self):
        assert BASE_VALUES["unverified"] == 1_000
        assert BASE_VALUES["verified"] == 10_000
        assert BASE_VALUES["premium"] == 100_000
