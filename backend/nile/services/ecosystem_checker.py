"""Ecosystem checker — verifies Solana programs against known registries and lists."""

import logging

import httpx

logger = logging.getLogger(__name__)

# Known audit firms in Solana ecosystem
KNOWN_AUDITORS = {
    "ottersec",
    "sec3",
    "neodyme",
    "halborn",
    "trail_of_bits",
    "quantstamp",
    "slowmist",
    "zellic",
    "kudelski",
    "certik",
    "oak_security",
    "offside_labs",
    "mad_shield",
}

# Well-known verified Solana programs
KNOWN_PROGRAMS = {
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "SPL Token",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": "Token-2022",
    "11111111111111111111111111111111": "System Program",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL": "Associated Token",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4": "Jupiter v6",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc": "Orca Whirlpool",
    "PhoeNiXZ8ByJGLkxNfZRnkUfjvmuYqLR89jjFHGqdXY": "Phoenix",
    "MERLuDFBMmsHnsBPZw2sDQZHvXFMwp8EdjudcU2HKky": "Mercurial",
    "srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX": "Serum v3",
    "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s": "Metaplex Token Metadata",
    "So1endDq2YkqhipRh3WViPa8hFb7GUEtLn6HkxCTCe2": "Solend",
    "MFv2hWf31Z9kbCa1snEPYctwafyhdvnV7FZnsebVacA": "Marinade Finance",
    "mv3ekLzLbnVPNxjSKvqBpU3ZeZXPQdEC3bp5MDEBG68": "Raydium AMM v4",
}


async def check_jupiter_strict_list(program_address: str) -> bool:
    """Check if a token/program is on the Jupiter strict verified list."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://token.jup.ag/strict",
                params={"address": program_address},
            )
            if resp.status_code == 200:
                tokens = resp.json()
                return any(t.get("address") == program_address for t in tokens)
    except Exception:
        logger.debug("Jupiter strict list check failed for %s", program_address)
    return False


async def check_known_program(program_address: str) -> str | None:
    """Check if program is a well-known verified Solana program."""
    return KNOWN_PROGRAMS.get(program_address)


async def check_program_age_days(program_address: str) -> int:
    """Estimate program age from first transaction."""
    from nile.services.chain_service import chain_service

    try:
        history = await chain_service.get_transaction_history(program_address, limit=1)
        if not history:
            return 0

        oldest = history[-1]
        block_time = oldest.get("block_time")
        if block_time:
            import time

            age_seconds = time.time() - block_time
            return max(0, int(age_seconds / 86400))
    except Exception:
        logger.debug("Failed to estimate program age for %s", program_address)

    return 0


async def assess_ecosystem_presence(program_address: str) -> dict:
    """Assess a program's ecosystem presence for the Name dimension.

    Returns:
        score: 0-20 ecosystem score
        details: breakdown of checks performed
    """
    score = 0.0
    details: dict = {}

    # Check if it's a known program (instant trust)
    known_name = await check_known_program(program_address)
    if known_name:
        details["known_program"] = known_name
        score += 15.0

    # Check Jupiter strict list
    on_jupiter = await check_jupiter_strict_list(program_address)
    details["jupiter_strict_list"] = on_jupiter
    if on_jupiter:
        score += 10.0

    # Check program age
    age_days = await check_program_age_days(program_address)
    details["age_days"] = age_days
    if age_days > 365:
        score += 5.0
    elif age_days > 90:
        score += 3.0
    elif age_days > 30:
        score += 1.0

    details["ecosystem_score"] = min(20.0, score)
    return details
