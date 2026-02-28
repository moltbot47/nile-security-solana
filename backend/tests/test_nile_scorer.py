"""Tests for the NILE scoring engine — Solana-adapted."""

from nile.services.nile_scorer import (
    EssenceInputs,
    ImageInputs,
    LikenessInputs,
    NameInputs,
    compute_essence_score,
    compute_image_score,
    compute_likeness_score,
    compute_name_score,
    compute_nile_score,
)

# --- Name dimension tests ---


def test_name_score_verified_program():
    inputs = NameInputs(
        is_verified=True, audit_count=3, age_days=730, team_identified=True, ecosystem_score=15.0
    )
    score, details = compute_name_score(inputs)
    assert score >= 80.0
    assert details["source_verified"] == 20.0
    assert details["team_identification"] == 20.0


def test_name_score_unverified_anonymous():
    inputs = NameInputs(is_verified=False, audit_count=0, age_days=0, team_identified=False)
    score, _ = compute_name_score(inputs)
    assert score == 5.0  # Only partial team score


def test_name_score_with_security_txt():
    inputs = NameInputs(
        is_verified=True,
        on_security_txt=True,
        team_identified=True,
        ecosystem_score=10.0,
    )
    score, details = compute_name_score(inputs)
    assert details["security_txt"] == 2.0
    assert score >= 50.0


def test_name_score_new_program():
    inputs = NameInputs(is_verified=True, age_days=7, team_identified=False)
    score, details = compute_name_score(inputs)
    assert details["maturity"] < 5.0  # Very new program


# --- Image dimension tests ---


def test_image_score_clean_program():
    inputs = ImageInputs(
        missing_signer_checks=0,
        pda_seed_collisions=0,
        unchecked_arithmetic=0,
        missing_owner_checks=0,
        unsafe_cpi_calls=0,
        unvalidated_accounts=0,
        trend=5.0,
    )
    score, _ = compute_image_score(inputs)
    assert score == 100.0  # Capped at 100


def test_image_score_missing_signers():
    inputs = ImageInputs(missing_signer_checks=2)
    score, details = compute_image_score(inputs)
    assert score == 60.0  # 100 - 2*20
    assert details["missing_signer_checks"] == 2


def test_image_score_multiple_vulns():
    inputs = ImageInputs(
        missing_signer_checks=1,
        pda_seed_collisions=1,
        unsafe_cpi_calls=1,
    )
    score, _ = compute_image_score(inputs)
    assert score == 50.0  # 100 - 20 - 15 - 15


def test_image_score_with_patch_bonus():
    inputs = ImageInputs(
        missing_signer_checks=1,
        avg_patch_time_days=2.0,
    )
    score, details = compute_image_score(inputs)
    # 100 - 20 (signer) + 8 (patch bonus: 10-2) = 88
    assert score == 88.0
    assert details["patch_cadence_bonus"] == 8.0


# --- Likeness dimension tests ---


def test_likeness_score_no_patterns():
    inputs = LikenessInputs()
    score, _ = compute_likeness_score(inputs)
    assert score == 100.0


def test_likeness_score_high_confidence_match():
    inputs = LikenessInputs(exploit_pattern_matches=[{"confidence": 0.9}, {"confidence": 0.7}])
    score, details = compute_likeness_score(inputs)
    assert score == 70.0  # 100 - 20 - 10
    assert details["exploit_match_count"] == 2


def test_likeness_score_rug_similarity():
    inputs = LikenessInputs(rug_pattern_similarity=0.8)
    score, details = compute_likeness_score(inputs)
    assert score == 76.0  # 100 - 0.8*30
    assert details["rug_similarity"] == 0.8


def test_likeness_score_static_findings():
    inputs = LikenessInputs(
        static_analysis_findings=[
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "low"},
        ]
    )
    score, details = compute_likeness_score(inputs)
    assert score == 62.0  # 100 - 20 - 15 - 3
    assert details["static_finding_count"] == 3


# --- Essence dimension tests ---


def test_essence_score_well_tested():
    inputs = EssenceInputs(
        test_coverage_pct=90.0,
        avg_instruction_complexity=3.0,
        upgrade_authority_active=False,
        has_timelock=True,
        cpi_call_count=2,
    )
    score, _ = compute_essence_score(inputs)
    assert score >= 85.0


def test_essence_score_risky_program():
    inputs = EssenceInputs(
        test_coverage_pct=10.0,
        avg_instruction_complexity=15.0,
        upgrade_authority_active=True,
        upgrade_authority_is_multisig=False,
        has_timelock=False,
        cpi_call_count=10,
    )
    score, details = compute_essence_score(inputs)
    assert score < 30.0
    assert details["upgrade_authority_active"] is True


def test_essence_upgrade_multisig_mitigates():
    # Single signer upgrade
    inputs_single = EssenceInputs(
        upgrade_authority_active=True,
        upgrade_authority_is_multisig=False,
        has_timelock=False,
    )
    score_single, _ = compute_essence_score(inputs_single)

    # Multisig upgrade
    inputs_multi = EssenceInputs(
        upgrade_authority_active=True,
        upgrade_authority_is_multisig=True,
        has_timelock=True,
    )
    score_multi, _ = compute_essence_score(inputs_multi)

    assert score_multi > score_single  # Multisig mitigates risk


# --- Composite score tests ---


def test_composite_nile_score():
    result = compute_nile_score(
        name_inputs=NameInputs(is_verified=True, audit_count=2, age_days=365, team_identified=True),
        image_inputs=ImageInputs(missing_signer_checks=0, unsafe_cpi_calls=1),
        likeness_inputs=LikenessInputs(
            static_analysis_findings=[{"severity": "medium"}],
            exploit_pattern_matches=[{"confidence": 0.5}],
        ),
        essence_inputs=EssenceInputs(test_coverage_pct=80.0, avg_instruction_complexity=6.0),
    )
    assert 0 <= result.total_score <= 100
    assert result.grade in ("A+", "A", "B", "C", "D", "F")
    assert "name" in result.details
    assert "image" in result.details
    assert "likeness" in result.details
    assert "essence" in result.details


def test_grade_assignment():
    result = compute_nile_score(
        name_inputs=NameInputs(
            is_verified=True,
            audit_count=3,
            age_days=730,
            team_identified=True,
            ecosystem_score=20,
        ),
        image_inputs=ImageInputs(
            missing_signer_checks=0,
            pda_seed_collisions=0,
            trend=5.0,
        ),
        likeness_inputs=LikenessInputs(),
        essence_inputs=EssenceInputs(test_coverage_pct=95, avg_instruction_complexity=3),
    )
    assert result.grade == "A+"
    assert result.total_score >= 90


def test_grade_f_for_terrible_program():
    result = compute_nile_score(
        name_inputs=NameInputs(),
        image_inputs=ImageInputs(
            missing_signer_checks=3,
            unsafe_cpi_calls=2,
            pda_seed_collisions=2,
        ),
        likeness_inputs=LikenessInputs(
            exploit_pattern_matches=[{"confidence": 0.95}],
            rug_pattern_similarity=0.9,
        ),
        essence_inputs=EssenceInputs(
            upgrade_authority_active=True,
            has_timelock=False,
            cpi_call_count=15,
        ),
    )
    assert result.grade == "F"
    assert result.total_score < 50
