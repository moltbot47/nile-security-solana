use anchor_lang::prelude::*;
use crate::state::{AgentProfile, OracleReport, VoteRecord};
use crate::errors::NileError;

#[derive(Accounts)]
pub struct VoteReport<'info> {
    #[account(mut)]
    pub report: Account<'info, OracleReport>,

    #[account(
        init,
        payer = agent,
        space = 8 + VoteRecord::INIT_SPACE,
        seeds = [b"vote", report.key().as_ref(), agent.key().as_ref()],
        bump,
    )]
    pub vote_record: Account<'info, VoteRecord>,

    #[account(
        mut,
        seeds = [b"agent", agent.key().as_ref()],
        bump = agent_profile.bump,
    )]
    pub agent_profile: Account<'info, AgentProfile>,

    #[account(mut)]
    pub agent: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<VoteReport>, approve: bool) -> Result<()> {
    require!(!ctx.accounts.report.finalized, NileError::ReportAlreadyFinalized);
    require!(ctx.accounts.agent_profile.is_active, NileError::AgentSuspended);

    // Prevent submitter from double-voting (they auto-confirmed on submission)
    require!(
        ctx.accounts.agent.key() != ctx.accounts.report.submitter,
        NileError::SelfVoteNotAllowed
    );

    let report = &mut ctx.accounts.report;

    // Record vote
    if approve {
        report.confirmations += 1;
    } else {
        report.rejections += 1;
    }

    // Check if quorum reached
    if report.confirmations >= report.required_quorum {
        report.finalized = true;
        report.accepted = true;
        report.finalized_at = Clock::get()?.unix_timestamp;
    } else if report.rejections > (report.required_quorum / 2) {
        // Impossible to reach quorum — auto-reject
        report.finalized = true;
        report.accepted = false;
        report.finalized_at = Clock::get()?.unix_timestamp;
    }

    // Record the vote
    let vote = &mut ctx.accounts.vote_record;
    vote.version = 1;
    vote.report = ctx.accounts.report.key();
    vote.agent = ctx.accounts.agent.key();
    vote.approved = approve;
    vote.voted_at = Clock::get()?.unix_timestamp;
    vote.bump = ctx.bumps.vote_record;

    // Update agent stats
    ctx.accounts.agent_profile.total_votes += 1;
    ctx.accounts.agent_profile.points += 2;

    Ok(())
}
