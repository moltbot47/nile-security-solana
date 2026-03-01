"""Deep tests for onchain_writer — submit_score_onchain + register_program_onchain."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_solana_modules():
    """Build a complete mock module tree for solders + solana."""
    mock_pubkey_cls = MagicMock()
    mock_pubkey_cls.from_string = MagicMock(
        side_effect=lambda s: MagicMock(
            __bytes__=lambda _: b"\x00" * 32,
        )
    )
    mock_pubkey_cls.from_bytes = MagicMock(
        side_effect=lambda b: MagicMock(
            __str__=lambda _: "MockPubkey",
        )
    )
    mock_pubkey_cls.find_program_address = MagicMock(
        return_value=(MagicMock(__str__=lambda _: "PDAAddr"), 255)
    )

    mock_keypair_cls = MagicMock()
    mock_deployer = MagicMock()
    mock_deployer.pubkey.return_value = MagicMock(
        __bytes__=lambda _: b"\xaa" * 32,
        __str__=lambda _: "DeployerPubkey",
    )
    mock_keypair_cls.from_bytes = MagicMock(return_value=mock_deployer)

    mock_instruction_cls = MagicMock()
    mock_account_meta_cls = MagicMock()

    mock_message_cls = MagicMock()
    mock_message_cls.new_with_blockhash = MagicMock(return_value=MagicMock())

    mock_tx_cls = MagicMock()
    mock_tx_cls.new = MagicMock(return_value=MagicMock())

    mock_sys_program_id = MagicMock()

    mock_async_client_cls = MagicMock()
    mock_client_instance = AsyncMock()
    blockhash_resp = MagicMock()
    blockhash_resp.value.blockhash = "MockBlockhash123"
    mock_client_instance.get_latest_blockhash = AsyncMock(return_value=blockhash_resp)
    send_result = MagicMock()
    send_result.value = "TxSig123ABC"
    mock_client_instance.send_transaction = AsyncMock(return_value=send_result)
    mock_client_instance.close = AsyncMock()
    mock_async_client_cls.return_value = mock_client_instance

    modules = {
        "solders": MagicMock(),
        "solders.pubkey": MagicMock(Pubkey=mock_pubkey_cls),
        "solders.keypair": MagicMock(Keypair=mock_keypair_cls),
        "solders.instruction": MagicMock(
            Instruction=mock_instruction_cls,
            AccountMeta=mock_account_meta_cls,
        ),
        "solders.message": MagicMock(Message=mock_message_cls),
        "solders.transaction": MagicMock(Transaction=mock_tx_cls),
        "solders.system_program": MagicMock(ID=mock_sys_program_id),
        "solana": MagicMock(),
        "solana.rpc": MagicMock(),
        "solana.rpc.async_api": MagicMock(AsyncClient=mock_async_client_cls),
        "base58": MagicMock(b58decode=MagicMock(return_value=b"\x01" * 64)),
    }
    return modules


@pytest.mark.asyncio
class TestSubmitScoreOnchain:
    async def test_disabled_returns_none(self):
        with patch("nile.services.onchain_writer.settings") as mock_settings:
            mock_settings.program_id = ""
            mock_settings.deployer_private_key = ""
            from nile.services.onchain_writer import submit_score_onchain

            result = await submit_score_onchain("SomeAddr", 90, 85, 80, 75)
            assert result is None

    async def test_success_returns_tx_sig(self):
        mods = _mock_solana_modules()
        with (
            patch("nile.services.onchain_writer._is_enabled", return_value=True),
            patch("nile.services.onchain_writer.settings") as mock_settings,
            patch.dict("sys.modules", mods),
        ):
            mock_settings.solana_rpc_url = "https://api.devnet.solana.com"
            mock_settings.deployer_private_key = "DeployerKey"

            from nile.services.onchain_writer import submit_score_onchain

            result = await submit_score_onchain(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                90,
                85,
                80,
                75,
                details_uri="ipfs://QmTest",
            )
            assert result == "TxSig123ABC"

    async def test_import_error_returns_none(self):
        """When solders not installed, returns None gracefully."""
        with patch("nile.services.onchain_writer.settings") as mock_settings:
            mock_settings.program_id = "SomeProgram"
            mock_settings.deployer_private_key = "SomeKey"

            from nile.services.onchain_writer import submit_score_onchain

            # Without solders installed, the import inside will fail
            result = await submit_score_onchain("Addr", 90, 85, 80, 75)
            assert result is None

    async def test_exception_returns_none(self):
        """Generic exception returns None."""
        mods = _mock_solana_modules()
        # Make b58decode raise
        mods["base58"].b58decode = MagicMock(side_effect=RuntimeError("decode fail"))

        with (
            patch("nile.services.onchain_writer._is_enabled", return_value=True),
            patch.dict("sys.modules", mods),
        ):
            from nile.services.onchain_writer import submit_score_onchain

            result = await submit_score_onchain("Addr", 90, 85, 80, 75)
            assert result is None


@pytest.mark.asyncio
class TestRegisterProgramOnchain:
    async def test_disabled_returns_none(self):
        with patch("nile.services.onchain_writer.settings") as mock_settings:
            mock_settings.program_id = ""
            mock_settings.deployer_private_key = ""
            from nile.services.onchain_writer import register_program_onchain

            result = await register_program_onchain("Addr", "TestProgram")
            assert result is None

    async def test_success_returns_tx_sig(self):
        mods = _mock_solana_modules()
        with (
            patch("nile.services.onchain_writer._is_enabled", return_value=True),
            patch("nile.services.onchain_writer.settings") as mock_settings,
            patch.dict("sys.modules", mods),
        ):
            mock_settings.solana_rpc_url = "https://api.devnet.solana.com"
            mock_settings.deployer_private_key = "Key"

            from nile.services.onchain_writer import register_program_onchain

            result = await register_program_onchain(
                "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
                "Token Program",
            )
            assert result == "TxSig123ABC"

    async def test_exception_returns_none(self):
        mods = _mock_solana_modules()
        mods["base58"].b58decode = MagicMock(side_effect=ValueError("bad key"))

        with (
            patch("nile.services.onchain_writer._is_enabled", return_value=True),
            patch.dict("sys.modules", mods),
        ):
            from nile.services.onchain_writer import register_program_onchain

            result = await register_program_onchain("Addr", "Name")
            assert result is None


@pytest.mark.asyncio
class TestLoadIdl:
    def test_idl_not_found(self):
        from nile.services.onchain_writer import _load_idl

        with patch("nile.services.onchain_writer._IDL_PATH") as mock_path:
            mock_path.exists.return_value = False
            result = _load_idl()
            assert result is None

    def test_idl_found(self):
        from nile.services.onchain_writer import _load_idl

        with patch("nile.services.onchain_writer._IDL_PATH") as mock_path:
            mock_path.exists.return_value = True
            mock_path.read_text.return_value = '{"version": "0.1.0"}'
            result = _load_idl()
            assert result == {"version": "0.1.0"}
