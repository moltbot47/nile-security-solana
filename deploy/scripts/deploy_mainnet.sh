#!/usr/bin/env bash
# deploy_mainnet.sh — Build, deploy, and initialize NILE Security on Solana mainnet-beta.
#
# DANGER: This deploys to MAINNET. Real SOL will be spent.
#
# Prerequisites:
#   - Rust / Cargo installed
#   - Solana CLI installed (solana --version)
#   - Anchor CLI installed (anchor --version)
#   - Funded deployer keypair (need ~3 SOL for program deploy)
#   - NILE_DEPLOYER_KEYPAIR env var or keypair at specified path
#
# Usage:
#   NILE_DEPLOYER_KEYPAIR=/path/to/deployer.json ./deploy/scripts/deploy_mainnet.sh
#
# Safety:
#   - Requires explicit --confirm flag to actually deploy
#   - Requires minimum balance check (3 SOL)
#   - Saves deployment info for rollback reference

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  NILE Security — MAINNET Deployment              ║${NC}"
echo -e "${RED}║  This will deploy to Solana mainnet-beta.        ║${NC}"
echo -e "${RED}║  Real SOL will be spent. This is NOT reversible. ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════╝${NC}"
echo ""

# --- Safety: require --confirm ---
if [[ "${1:-}" != "--confirm" ]]; then
    echo -e "${YELLOW}Dry-run mode. Pass --confirm to actually deploy.${NC}"
    echo ""
    DRY_RUN=true
else
    DRY_RUN=false
fi

# --- 1. Check prerequisites ---
echo "[1/8] Checking prerequisites..."
for cmd in solana anchor cargo; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}ERROR: $cmd not found. Please install it first.${NC}"
        exit 1
    fi
done

# --- 2. Configure deployer keypair ---
KEYPAIR="${NILE_DEPLOYER_KEYPAIR:-$HOME/.config/solana/mainnet-deployer.json}"
if [ ! -f "$KEYPAIR" ]; then
    echo -e "${RED}ERROR: Deployer keypair not found at $KEYPAIR${NC}"
    echo "  Set NILE_DEPLOYER_KEYPAIR=/path/to/keypair.json"
    echo "  Generate one with: solana-keygen new -o $KEYPAIR"
    exit 1
fi

echo -e "${GREEN}  Deployer keypair: $KEYPAIR${NC}"

# --- 3. Configure for mainnet ---
echo ""
echo "[2/8] Configuring Solana CLI for mainnet-beta..."
solana config set --url https://api.mainnet-beta.solana.com --keypair "$KEYPAIR"

DEPLOYER=$(solana address -k "$KEYPAIR")
BALANCE=$(solana balance "$DEPLOYER" | awk '{print $1}')
echo "  Deployer: $DEPLOYER"
echo "  Balance:  $BALANCE SOL"

# Minimum 3 SOL for program deployment
MIN_BALANCE=3
if (( $(echo "$BALANCE < $MIN_BALANCE" | bc -l) )); then
    echo -e "${RED}ERROR: Insufficient balance. Need at least $MIN_BALANCE SOL, have $BALANCE SOL.${NC}"
    echo "  Fund the deployer wallet: $DEPLOYER"
    exit 1
fi

echo -e "${GREEN}  Balance OK ($BALANCE >= $MIN_BALANCE SOL)${NC}"

# --- 4. Build ---
echo ""
echo "[3/8] Building Anchor programs..."
cd "$PROJECT_ROOT"
anchor build

# --- 5. Extract program ID ---
PROGRAM_KEYPAIR="$PROJECT_ROOT/target/deploy/nile_security-keypair.json"
if [ ! -f "$PROGRAM_KEYPAIR" ]; then
    echo -e "${RED}ERROR: Program keypair not found at $PROGRAM_KEYPAIR${NC}"
    exit 1
fi

PROGRAM_ID=$(solana address -k "$PROGRAM_KEYPAIR")
echo ""
echo "[4/8] Program ID: $PROGRAM_ID"

# --- 6. Update program ID in source ---
echo "[5/8] Updating program IDs in source files..."

sed -i '' "s/declare_id!(\"[^\"]*\")/declare_id!(\"$PROGRAM_ID\")/" \
    "$PROJECT_ROOT/programs/nile_security/src/lib.rs"

# Update all Anchor.toml sections
for section in localnet devnet mainnet; do
    sed -i '' "s/nile_security = \"[^\"]*\"/nile_security = \"$PROGRAM_ID\"/" \
        "$PROJECT_ROOT/Anchor.toml"
done

echo "  Rebuilding with updated program ID..."
anchor build

# --- 7. Deploy ---
echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[6/8] SKIPPED — dry-run mode. Would deploy program: $PROGRAM_ID${NC}"
    echo -e "${YELLOW}[7/8] SKIPPED — dry-run mode. Would initialize authority.${NC}"
else
    echo "[6/8] Deploying to mainnet-beta..."
    echo -e "${RED}  Deploying in 5 seconds... Ctrl+C to abort.${NC}"
    sleep 5

    anchor deploy --provider.cluster mainnet --provider.wallet "$KEYPAIR"
    echo -e "${GREEN}  Deployed! Program ID: $PROGRAM_ID${NC}"

    # --- 8. Initialize ---
    echo ""
    echo "[7/8] Initializing NILE authority..."

    cat > /tmp/nile_init_mainnet.ts << 'INITEOF'
import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { NileSecurity } from "../target/types/nile_security";
import { PublicKey, SystemProgram } from "@solana/web3.js";

async function main() {
    const provider = anchor.AnchorProvider.env();
    anchor.setProvider(provider);
    const program = anchor.workspace.NileSecurity as Program<NileSecurity>;

    const [authorityPda] = PublicKey.findProgramAddressSync(
        [Buffer.from("nile_authority")],
        program.programId,
    );

    try {
        await program.methods
            .initialize()
            .accounts({
                authority: authorityPda,
                admin: provider.wallet.publicKey,
                systemProgram: SystemProgram.programId,
            })
            .rpc();
        console.log("  Authority initialized at:", authorityPda.toBase58());
    } catch (e: any) {
        if (e.message?.includes("already in use")) {
            console.log("  Authority already initialized at:", authorityPda.toBase58());
        } else {
            throw e;
        }
    }

    const agentKey = process.env.NILE_AGENT_PUBKEY;
    if (agentKey) {
        const agentPubkey = new PublicKey(agentKey);
        const [agentPda] = PublicKey.findProgramAddressSync(
            [Buffer.from("agent"), agentPubkey.toBuffer()],
            program.programId,
        );

        try {
            await program.methods
                .authorizeAgent(agentPubkey)
                .accounts({
                    authority: authorityPda,
                    agentProfile: agentPda,
                    admin: provider.wallet.publicKey,
                    systemProgram: SystemProgram.programId,
                })
                .rpc();
            console.log("  Agent authorized:", agentKey);
        } catch (e: any) {
            console.log("  Agent already authorized or error:", e.message);
        }
    }
}

main().catch(console.error);
INITEOF

    ANCHOR_PROVIDER_URL=https://api.mainnet-beta.solana.com \
    ANCHOR_WALLET="$KEYPAIR" \
    npx ts-node /tmp/nile_init_mainnet.ts
fi

# --- 9. Save deployment info ---
echo ""
echo "[8/8] Saving deployment info..."

DEPLOY_DIR="$PROJECT_ROOT/deploy"
DEPLOY_FILE="$DEPLOY_DIR/mainnet-deployment.json"
cat > "$DEPLOY_FILE" << EOF
{
    "network": "mainnet-beta",
    "program_id": "$PROGRAM_ID",
    "deployer": "$DEPLOYER",
    "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "anchor_version": "$(anchor --version 2>/dev/null || echo 'unknown')",
    "solana_version": "$(solana --version 2>/dev/null | awk '{print $2}' || echo 'unknown')",
    "dry_run": $DRY_RUN
}
EOF

echo -e "${GREEN}  Saved to: $DEPLOY_FILE${NC}"
echo ""
echo "═══════════════════════════════════════════════════"
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}  DRY RUN complete. No changes made to mainnet.${NC}"
    echo -e "${YELLOW}  Run with --confirm to deploy for real.${NC}"
else
    echo -e "${GREEN}  MAINNET deployment complete!${NC}"
fi
echo "  Program ID: $PROGRAM_ID"
echo "  Network:    mainnet-beta"
echo "  Explorer:   https://explorer.solana.com/address/$PROGRAM_ID"
echo ""
echo "Update your production .env:"
echo "  NILE_PROGRAM_ID=$PROGRAM_ID"
echo "  NILE_SOLANA_RPC_URL=https://api.mainnet-beta.solana.com"
echo "  NILE_SOLANA_NETWORK=mainnet-beta"
echo "  NILE_PYTH_SOL_USD_FEED=H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG"
echo "═══════════════════════════════════════════════════"
