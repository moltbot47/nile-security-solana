"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "NILE Security (Solana)"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://nile:nile@localhost:5432/nile_solana"
    database_echo: bool = False

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI APIs
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    default_model: str = "claude-opus-4-6"

    # Security
    api_key: str = ""
    jwt_secret: str = "nile-dev-secret-change-me"  # noqa: S105
    cors_origins: list[str] = ["http://localhost:3000"]

    # Discord
    discord_token: str = ""
    discord_guild_id: str = ""

    # Chain / Solana
    chain: str = "solana"
    solana_rpc_url: str = "https://api.devnet.solana.com"
    solana_network: str = "devnet"  # devnet | testnet | mainnet-beta
    deployer_private_key: str = ""
    program_id: str = ""  # Main NILE program (factory + router)
    oracle_program_id: str = ""  # Oracle consensus program
    treasury_program_id: str = ""  # Fee management program

    # Pyth Oracle (SOL/USD price feed)
    pyth_sol_usd_feed: str = "J83w4HKfqxwcq3BEMMkPFSppX3gqekLyLJBexebFVkix"  # Pyth SOL/USD devnet

    # Legacy EVM fields (kept for dual-chain future)
    chain_rpc_url: str = ""
    chain_id: int = 0
    factory_address: str = ""
    router_address: str = ""
    treasury_address: str = ""
    oracle_address: str = ""
    eth_price_feed: str = ""

    model_config = {"env_file": ".env", "env_prefix": "NILE_"}


settings = Settings()
