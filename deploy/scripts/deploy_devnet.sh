#!/usr/bin/env bash
# deploy_devnet.sh — Build, deploy, and initialize NILE Security on Solana devnet.
#
# Prerequisites:
#   - Rust / Cargo installed
#   - Solana CLI installed (solana --version)
#   - Anchor CLI installed (anchor --version)
#   - Deployer keypair at ~/.config/solana/id.json with devnet SOL
#
# Usage:
#   ./deploy/scripts/deploy_devnet.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=== NILE Security — Devnet Deployment ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# --- 1. Check prerequisites ---
for cmd in solana anchor cargo; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: $cmd not found. Please install it first."
    exit 1
  fi
done

# --- 2. Configure for devnet ---
echo "[1/7] Configuring Solana CLI for devnet..."
solana config set --url https://api.devnet.solana.com

DEPLOYER=$(solana address)
BALANCE=$(solana balance | awk '{print $1}')
echo "  Deployer: $DEPLOYER"
echo "  Balance:  $BALANCE SOL"

if (( $(echo "$BALANCE < 2" | bc -l) )); then
  echo "  Requesting airdrop (need >= 2 SOL for deploy)..."
  solana airdrop 2
  sleep 5
fi

# --- 3. Build ---
echo ""
echo "[2/7] Building Anchor programs..."
cd "$PROJECT_ROOT"
anchor build

# --- 4. Extract program ID ---
PROGRAM_KEYPAIR="$PROJECT_ROOT/target/deploy/nile_security-keypair.json"
if [ ! -f "$PROGRAM_KEYPAIR" ]; then
  echo "ERROR: Keypair not found at $PROGRAM_KEYPAIR"
  echo "  Run 'anchor build' first."
  exit 1
fi

PROGRAM_ID=$(solana address -k "$PROGRAM_KEYPAIR")
echo ""
echo "[3/7] Program ID: $PROGRAM_ID"

# --- 5. Update program ID in source ---
echo "[4/7] Updating program IDs in source files..."

# Update lib.rs
sed -i '' "s/declare_id!(\"[^\"]*\")/declare_id!(\"$PROGRAM_ID\")/" \
  "$PROJECT_ROOT/programs/nile_security/src/lib.rs"

# Update Anchor.toml
sed -i '' "s/nile_security = \"[^\"]*\"/nile_security = \"$PROGRAM_ID\"/" \
  "$PROJECT_ROOT/Anchor.toml"

# Rebuild with correct ID
echo "  Rebuilding with updated program ID..."
anchor build

# --- 6. Deploy ---
echo ""
echo "[5/7] Deploying to devnet..."
anchor deploy --provider.cluster devnet

echo "  Deployed! Program ID: $PROGRAM_ID"

# --- 7. Initialize (call the initialize instruction) ---
echo ""
echo "[6/7] Initializing NILE authority..."

# Use anchor's test framework to call initialize
cat > /tmp/nile_init.ts << 'INITEOF'
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

  // Optionally authorize a backend agent
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

npx ts-node /tmp/nile_init.ts

# --- 8. Save deployment info ---
echo ""
echo "[7/7] Saving deployment info..."

DEPLOY_FILE="$PROJECT_ROOT/deploy/devnet-deployment.json"
cat > "$DEPLOY_FILE" << EOF
{
  "network": "devnet",
  "program_id": "$PROGRAM_ID",
  "deployer": "$DEPLOYER",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "anchor_version": "$(anchor --version)",
  "solana_version": "$(solana --version | awk '{print $2}')"
}
EOF

echo "  Saved to: $DEPLOY_FILE"
echo ""
echo "=== Deployment complete ==="
echo "  Program ID: $PROGRAM_ID"
echo "  Network:    devnet"
echo "  Explorer:   https://explorer.solana.com/address/$PROGRAM_ID?cluster=devnet"
echo ""
echo "Update your .env:"
echo "  NILE_PROGRAM_ID=$PROGRAM_ID"
