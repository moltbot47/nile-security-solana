# NILE Scoring Methodology

## Overview

NILE (Name, Image, Likeness, Essence) is a 4-dimensional security scoring framework that evaluates Solana programs and tokens on a 0-100 scale. Each dimension contributes 25% to the composite score.

## Dimension 1: Name (Identity & Reputation)

Evaluates the program's public identity, team reputation, and ecosystem standing.

| Factor | Weight | Score Range |
|--------|--------|-------------|
| Verified source (on-chain) | High | +15 if verified |
| Audit count | High | +5 per audit (max 15) |
| Program age | Medium | +0.01/day (max 10) |
| Team identified | Medium | +10 if known |
| Ecosystem score (Jupiter, Birdeye) | Medium | Up to +20 |
| security.txt present | Low | +5 |

**Base score:** 25 (unverified, anonymous) to 100 (fully verified, multi-audited)

## Dimension 2: Image (Security Posture)

Static analysis of the program's instruction structure via IDL.

| Finding | Penalty |
|---------|---------|
| Missing signer check (mutable account) | -8 per |
| PDA seed collision risk | -12 per |
| Unchecked arithmetic | -5 per |
| Missing owner check | -8 per |
| Unsafe CPI call | -10 per |
| Unvalidated account | -5 per |

**Base score:** 100 (deductions applied). Minimum: 0.

**Trend bonus:** +/- 5 points based on recent score trajectory.

## Dimension 3: Likeness (Exploit Pattern Matching)

Compares program characteristics against a database of known Solana exploits.

| Factor | Impact |
|--------|--------|
| Exploit pattern match (>0.7 confidence) | -20 per (max -40) |
| Rug pull similarity score | -30 * similarity |
| Static analysis critical finding | -15 per |
| Static analysis high finding | -8 per |

**Pattern database:** `data/exploit_patterns/solana_exploits.json`

Categories: reentrancy, access_control, arithmetic_overflow, oracle_manipulation, rug_pull, flash_loan, pda_collision, cpi_hijacking, account_confusion, state_manipulation

## Dimension 4: Essence (Code Quality & Governance)

Evaluates code quality, upgrade safety, and governance structure.

| Factor | Weight | Score Range |
|--------|--------|-------------|
| Test coverage | High | coverage_pct * 0.3 (max 30) |
| Instruction complexity | Medium | Penalty above 10 avg |
| Upgrade authority active | Critical | -25 if active |
| Upgrade authority is multisig | Medium | +15 mitigates upgrade risk |
| Timelock present | Medium | +10 |
| CPI call count | Low | -2 per call above 5 |

## Composite Score & Grades

```
total_score = (name * 0.25) + (image * 0.25) + (likeness * 0.25) + (essence * 0.25)
```

| Score | Grade | Interpretation |
|-------|-------|----------------|
| 90-100 | A+ | Excellent — minimal risk |
| 80-89 | A | Strong — well-audited, low vulnerability |
| 70-79 | B | Good — some improvements recommended |
| 60-69 | C | Fair — notable risks present |
| 50-59 | D | Poor — significant vulnerabilities |
| 0-49 | F | Critical — high risk, avoid interaction |

## Token-Specific Analysis

When a token mint (not a program) is scanned:

- **Mint authority active** → rug risk indicator
- **Freeze authority active** → funds can be frozen
- **Low supply** → concentration risk
- **No IDL** → scored conservatively on Image dimension

## Known Exploit Patterns

| Pattern | Severity | CWE |
|---------|----------|-----|
| Reentrancy | Critical | CWE-841 |
| Missing Access Control | Critical | CWE-284 |
| Arithmetic Overflow | High | CWE-190 |
| Oracle Manipulation | Critical | CWE-345 |
| Rug Pull | Critical | CWE-506 |
| Flash Loan Attack | High | CWE-362 |
| PDA Collision | High | CWE-694 |
| CPI Hijacking | Critical | CWE-610 |
| Account Confusion | Medium | CWE-843 |
| State Manipulation | High | CWE-665 |
