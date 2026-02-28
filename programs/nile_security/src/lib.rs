use anchor_lang::prelude::*;

pub mod state;
pub mod instructions;
pub mod errors;

use instructions::*;

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod nile_security {
    use super::*;

    /// Register a new program for NILE scoring.
    pub fn register_program(
        ctx: Context<RegisterProgram>,
        program_address: Pubkey,
        name: String,
    ) -> Result<()> {
        instructions::register_program::handler(ctx, program_address, name)
    }

    /// Submit a NILE score for a registered program.
    pub fn submit_score(
        ctx: Context<SubmitScore>,
        name_score: u8,
        image_score: u8,
        likeness_score: u8,
        essence_score: u8,
        details_uri: String,
    ) -> Result<()> {
        instructions::submit_score::handler(
            ctx, name_score, image_score, likeness_score, essence_score, details_uri,
        )
    }

    /// Submit an oracle report (event that impacts a program's score).
    pub fn submit_report(
        ctx: Context<SubmitReport>,
        program_address: Pubkey,
        event_type: String,
        headline: String,
        impact_score: i8,
    ) -> Result<()> {
        instructions::submit_report::handler(
            ctx, program_address, event_type, headline, impact_score,
        )
    }

    /// Vote on an oracle report (agent consensus).
    pub fn vote_report(
        ctx: Context<VoteReport>,
        approve: bool,
    ) -> Result<()> {
        instructions::vote_report::handler(ctx, approve)
    }

    /// Initialize the NILE authority (one-time setup).
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        instructions::initialize::handler(ctx)
    }

    /// Authorize a scanning agent.
    pub fn authorize_agent(
        ctx: Context<AuthorizeAgent>,
        agent: Pubkey,
    ) -> Result<()> {
        instructions::authorize_agent::handler(ctx, agent)
    }
}
