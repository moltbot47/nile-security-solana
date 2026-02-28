import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { NileSecurity } from "../target/types/nile_security";
import { expect } from "chai";
import { Keypair, PublicKey, SystemProgram } from "@solana/web3.js";

describe("nile_security", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.NileSecurity as Program<NileSecurity>;
  const admin = provider.wallet;

  // Test keypairs
  const agentKeypair = Keypair.generate();
  const agent2Keypair = Keypair.generate();
  const targetProgram = Keypair.generate().publicKey;
  const targetProgram2 = Keypair.generate().publicKey;

  // PDA addresses (derived in tests)
  let authorityPda: PublicKey;
  let authorityBump: number;
  let programProfilePda: PublicKey;
  let agentProfilePda: PublicKey;
  let agent2ProfilePda: PublicKey;
  let reportPda: PublicKey;

  before(async () => {
    // Airdrop SOL to agent keypairs for transaction fees
    const sig1 = await provider.connection.requestAirdrop(
      agentKeypair.publicKey,
      2 * anchor.web3.LAMPORTS_PER_SOL,
    );
    await provider.connection.confirmTransaction(sig1);

    const sig2 = await provider.connection.requestAirdrop(
      agent2Keypair.publicKey,
      2 * anchor.web3.LAMPORTS_PER_SOL,
    );
    await provider.connection.confirmTransaction(sig2);

    // Derive PDAs
    [authorityPda, authorityBump] = PublicKey.findProgramAddressSync(
      [Buffer.from("nile_authority")],
      program.programId,
    );

    [programProfilePda] = PublicKey.findProgramAddressSync(
      [Buffer.from("program"), targetProgram.toBuffer()],
      program.programId,
    );

    [agentProfilePda] = PublicKey.findProgramAddressSync(
      [Buffer.from("agent"), agentKeypair.publicKey.toBuffer()],
      program.programId,
    );

    [agent2ProfilePda] = PublicKey.findProgramAddressSync(
      [Buffer.from("agent"), agent2Keypair.publicKey.toBuffer()],
      program.programId,
    );
  });

  // ─── 1. Initialize ───────────────────────────────────────

  describe("initialize", () => {
    it("creates the NILE authority", async () => {
      await program.methods
        .initialize()
        .accounts({
          authority: authorityPda,
          admin: admin.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      const authority = await program.account.nileAuthority.fetch(authorityPda);
      expect(authority.admin.toBase58()).to.equal(admin.publicKey.toBase58());
      expect(authority.agentCount).to.equal(0);
      expect(authority.totalScoresSubmitted.toNumber()).to.equal(0);
      expect(authority.totalReports.toNumber()).to.equal(0);
    });

    it("fails on double initialization", async () => {
      try {
        await program.methods
          .initialize()
          .accounts({
            authority: authorityPda,
            admin: admin.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        // Account already initialized — Anchor rejects init of existing PDA
        expect(err).to.exist;
      }
    });
  });

  // ─── 2. Authorize Agent ──────────────────────────────────

  describe("authorize_agent", () => {
    it("authorizes agent 1", async () => {
      await program.methods
        .authorizeAgent(agentKeypair.publicKey)
        .accounts({
          authority: authorityPda,
          agentProfile: agentProfilePda,
          admin: admin.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      const agent = await program.account.agentProfile.fetch(agentProfilePda);
      expect(agent.agentAddress.toBase58()).to.equal(
        agentKeypair.publicKey.toBase58(),
      );
      expect(agent.isActive).to.be.true;
      expect(agent.totalScores.toNumber()).to.equal(0);
      expect(agent.points.toNumber()).to.equal(0);

      const authority = await program.account.nileAuthority.fetch(authorityPda);
      expect(authority.agentCount).to.equal(1);
    });

    it("authorizes agent 2", async () => {
      await program.methods
        .authorizeAgent(agent2Keypair.publicKey)
        .accounts({
          authority: authorityPda,
          agentProfile: agent2ProfilePda,
          admin: admin.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      const authority = await program.account.nileAuthority.fetch(authorityPda);
      expect(authority.agentCount).to.equal(2);
    });

    it("rejects non-admin authorization", async () => {
      const fakeAgent = Keypair.generate();
      const [fakePda] = PublicKey.findProgramAddressSync(
        [Buffer.from("agent"), fakeAgent.publicKey.toBuffer()],
        program.programId,
      );
      try {
        await program.methods
          .authorizeAgent(fakeAgent.publicKey)
          .accounts({
            authority: authorityPda,
            agentProfile: fakePda,
            admin: agentKeypair.publicKey, // Not the admin
            systemProgram: SystemProgram.programId,
          })
          .signers([agentKeypair])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err).to.exist;
      }
    });
  });

  // ─── 3. Register Program ─────────────────────────────────

  describe("register_program", () => {
    it("registers a program for scoring", async () => {
      await program.methods
        .registerProgram(targetProgram, "Token Program")
        .accounts({
          profile: programProfilePda,
          registrant: admin.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.programAddress.toBase58()).to.equal(
        targetProgram.toBase58(),
      );
      expect(profile.name).to.equal("Token Program");
      expect(profile.totalScore).to.equal(0);
      expect(profile.grade).to.equal("F");
      expect(profile.scoreCount).to.equal(0);
    });

    it("rejects name longer than 64 chars", async () => {
      const [pda2] = PublicKey.findProgramAddressSync(
        [Buffer.from("program"), targetProgram2.toBuffer()],
        program.programId,
      );
      try {
        await program.methods
          .registerProgram(targetProgram2, "X".repeat(65))
          .accounts({
            profile: pda2,
            registrant: admin.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err.error?.errorCode?.code).to.equal("NameTooLong");
      }
    });
  });

  // ─── 4. Submit Score ──────────────────────────────────────

  describe("submit_score", () => {
    it("submits a NILE score as authorized agent", async () => {
      await program.methods
        .submitScore(85, 70, 90, 75, "ipfs://Qm_test_details_hash")
        .accounts({
          profile: programProfilePda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
        })
        .signers([agentKeypair])
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.nameScore).to.equal(85);
      expect(profile.imageScore).to.equal(70);
      expect(profile.likenessScore).to.equal(90);
      expect(profile.essenceScore).to.equal(75);
      expect(profile.totalScore).to.equal(80); // (85+70+90+75)/4 = 80
      expect(profile.grade).to.equal("A");
      expect(profile.scoreCount).to.equal(1);
      expect(profile.detailsUri).to.equal("ipfs://Qm_test_details_hash");

      const agent = await program.account.agentProfile.fetch(agentProfilePda);
      expect(agent.totalScores.toNumber()).to.equal(1);
      expect(agent.points.toNumber()).to.equal(10);

      const authority = await program.account.nileAuthority.fetch(authorityPda);
      expect(authority.totalScoresSubmitted.toNumber()).to.equal(1);
    });

    it("updates score on re-submit", async () => {
      await program.methods
        .submitScore(95, 92, 88, 96, "ipfs://Qm_updated_hash")
        .accounts({
          profile: programProfilePda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
        })
        .signers([agentKeypair])
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.totalScore).to.equal(92); // (95+92+88+96)/4 = 92.75 → 92
      expect(profile.grade).to.equal("A+");
      expect(profile.scoreCount).to.equal(2);
    });

    it("rejects score > 100", async () => {
      try {
        await program.methods
          .submitScore(101, 50, 50, 50, "")
          .accounts({
            profile: programProfilePda,
            agentProfile: agentProfilePda,
            authority: authorityPda,
            agent: agentKeypair.publicKey,
          })
          .signers([agentKeypair])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err.error?.errorCode?.code).to.equal("ScoreOutOfRange");
      }
    });

    it("rejects details_uri > 200 chars", async () => {
      try {
        await program.methods
          .submitScore(50, 50, 50, 50, "X".repeat(201))
          .accounts({
            profile: programProfilePda,
            agentProfile: agentProfilePda,
            authority: authorityPda,
            agent: agentKeypair.publicKey,
          })
          .signers([agentKeypair])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err.error?.errorCode?.code).to.equal("DetailsTooLong");
      }
    });
  });

  // ─── 5. Submit Report ─────────────────────────────────────

  describe("submit_report", () => {
    it("submits an oracle report", async () => {
      // Derive report PDA using current total_reports count (0)
      const authority = await program.account.nileAuthority.fetch(authorityPda);
      const reportIndex = authority.totalReports.toNumber();

      [reportPda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("report"),
          targetProgram.toBuffer(),
          new anchor.BN(reportIndex).toArrayLike(Buffer, "le", 8),
        ],
        program.programId,
      );

      await program.methods
        .submitReport(
          targetProgram,
          "exploit",
          "Critical vulnerability discovered in Token Program",
          -75,
        )
        .accounts({
          report: reportPda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([agentKeypair])
        .rpc();

      const report = await program.account.oracleReport.fetch(reportPda);
      expect(report.programAddress.toBase58()).to.equal(
        targetProgram.toBase58(),
      );
      expect(report.eventType).to.equal("exploit");
      expect(report.impactScore).to.equal(-75);
      expect(report.confirmations).to.equal(1); // Auto-confirmed by submitter
      expect(report.rejections).to.equal(0);
      expect(report.requiredQuorum).to.be.gte(1);

      const agent = await program.account.agentProfile.fetch(agentProfilePda);
      expect(agent.totalReports.toNumber()).to.equal(1);
      expect(agent.points.toNumber()).to.equal(25); // 10+10+5
    });

    it("rejects impact score out of range", async () => {
      const auth = await program.account.nileAuthority.fetch(authorityPda);
      const idx = auth.totalReports.toNumber();
      const [badPda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("report"),
          targetProgram.toBuffer(),
          new anchor.BN(idx).toArrayLike(Buffer, "le", 8),
        ],
        program.programId,
      );

      try {
        await program.methods
          .submitReport(targetProgram, "test", "Test", 127 as any)
          .accounts({
            report: badPda,
            agentProfile: agentProfilePda,
            authority: authorityPda,
            agent: agentKeypair.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([agentKeypair])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err).to.exist;
      }
    });
  });

  // ─── 6. Vote Report ──────────────────────────────────────

  describe("vote_report", () => {
    it("agent 2 votes to approve the report", async () => {
      const [votePda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("vote"),
          reportPda.toBuffer(),
          agent2Keypair.publicKey.toBuffer(),
        ],
        program.programId,
      );

      await program.methods
        .voteReport(true)
        .accounts({
          report: reportPda,
          voteRecord: votePda,
          agentProfile: agent2ProfilePda,
          agent: agent2Keypair.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .signers([agent2Keypair])
        .rpc();

      const report = await program.account.oracleReport.fetch(reportPda);
      expect(report.confirmations).to.equal(2);

      // With 2 agents, quorum = ceil(2*2/3) = 2, should be finalized
      expect(report.finalized).to.be.true;
      expect(report.accepted).to.be.true;

      const vote = await program.account.voteRecord.fetch(votePda);
      expect(vote.approved).to.be.true;

      const agent2 = await program.account.agentProfile.fetch(
        agent2ProfilePda,
      );
      expect(agent2.totalVotes.toNumber()).to.equal(1);
      expect(agent2.points.toNumber()).to.equal(2);
    });

    it("rejects voting on finalized report", async () => {
      const fakeVoter = Keypair.generate();
      const [fakeAgentPda] = PublicKey.findProgramAddressSync(
        [Buffer.from("agent"), fakeVoter.publicKey.toBuffer()],
        program.programId,
      );
      const [votePda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("vote"),
          reportPda.toBuffer(),
          fakeVoter.publicKey.toBuffer(),
        ],
        program.programId,
      );

      // This should fail because report is already finalized
      // (and fakeVoter is not an authorized agent)
      try {
        await program.methods
          .voteReport(false)
          .accounts({
            report: reportPda,
            voteRecord: votePda,
            agentProfile: fakeAgentPda,
            agent: fakeVoter.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([fakeVoter])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        expect(err).to.exist;
      }
    });

    it("prevents double voting (PDA already exists)", async () => {
      const [votePda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("vote"),
          reportPda.toBuffer(),
          agent2Keypair.publicKey.toBuffer(),
        ],
        program.programId,
      );

      try {
        await program.methods
          .voteReport(true)
          .accounts({
            report: reportPda,
            voteRecord: votePda,
            agentProfile: agent2ProfilePda,
            agent: agent2Keypair.publicKey,
            systemProgram: SystemProgram.programId,
          })
          .signers([agent2Keypair])
          .rpc();
        expect.fail("Should have thrown");
      } catch (err: any) {
        // VoteRecord PDA already exists — cannot init twice
        expect(err).to.exist;
      }
    });
  });

  // ─── 7. Grade assignment edge cases ───────────────────────

  describe("grade edge cases", () => {
    it("F grade for all zeros", async () => {
      await program.methods
        .submitScore(0, 0, 0, 0, "")
        .accounts({
          profile: programProfilePda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
        })
        .signers([agentKeypair])
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.totalScore).to.equal(0);
      expect(profile.grade).to.equal("F");
    });

    it("A+ grade for perfect scores", async () => {
      await program.methods
        .submitScore(100, 100, 100, 100, "")
        .accounts({
          profile: programProfilePda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
        })
        .signers([agentKeypair])
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.totalScore).to.equal(100);
      expect(profile.grade).to.equal("A+");
    });

    it("B grade for 70-79 range", async () => {
      await program.methods
        .submitScore(75, 70, 72, 78, "")
        .accounts({
          profile: programProfilePda,
          agentProfile: agentProfilePda,
          authority: authorityPda,
          agent: agentKeypair.publicKey,
        })
        .signers([agentKeypair])
        .rpc();

      const profile =
        await program.account.programProfile.fetch(programProfilePda);
      expect(profile.totalScore).to.equal(73); // (75+70+72+78)/4 = 73.75 → 73
      expect(profile.grade).to.equal("B");
    });
  });
});
