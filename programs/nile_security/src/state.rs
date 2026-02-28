use anchor_lang::prelude::*;

/// Global NILE authority — controls agent authorization.
#[account]
#[derive(InitSpace)]
pub struct NileAuthority {
    pub admin: Pubkey,
    pub agent_count: u32,
    pub total_scores_submitted: u64,
    pub total_reports: u64,
    pub bump: u8,
}

/// A registered Solana program being tracked by NILE.
#[account]
#[derive(InitSpace)]
pub struct ProgramProfile {
    pub program_address: Pubkey,
    #[max_len(64)]
    pub name: String,
    pub registrant: Pubkey,

    // Latest NILE scores (0-100 each)
    pub name_score: u8,
    pub image_score: u8,
    pub likeness_score: u8,
    pub essence_score: u8,
    pub total_score: u8,
    #[max_len(1)]
    pub grade: String,

    // Metadata
    pub score_count: u32,           // Number of times scored
    pub last_scored_at: i64,        // Unix timestamp
    pub registered_at: i64,         // Unix timestamp
    #[max_len(200)]
    pub details_uri: String,        // IPFS/Arweave URI for full score report

    pub bump: u8,
}

/// An authorized NILE scanning agent.
#[account]
#[derive(InitSpace)]
pub struct AgentProfile {
    pub agent_address: Pubkey,
    pub authorized_by: Pubkey,
    pub is_active: bool,
    pub total_scores: u64,
    pub total_reports: u64,
    pub total_votes: u64,
    pub points: u64,
    pub authorized_at: i64,
    pub bump: u8,
}

/// An oracle report submitted by an agent about a program event.
#[account]
#[derive(InitSpace)]
pub struct OracleReport {
    pub program_address: Pubkey,
    pub submitter: Pubkey,

    #[max_len(32)]
    pub event_type: String,         // "exploit", "audit_completed", "upgrade", etc.
    #[max_len(200)]
    pub headline: String,
    pub impact_score: i8,           // -100 to +100

    pub confirmations: u8,
    pub rejections: u8,
    pub required_quorum: u8,
    pub finalized: bool,
    pub accepted: bool,

    pub submitted_at: i64,
    pub finalized_at: i64,

    pub bump: u8,
}

/// Tracks whether an agent has voted on a specific report.
#[account]
#[derive(InitSpace)]
pub struct VoteRecord {
    pub report: Pubkey,
    pub agent: Pubkey,
    pub approved: bool,
    pub voted_at: i64,
    pub bump: u8,
}
