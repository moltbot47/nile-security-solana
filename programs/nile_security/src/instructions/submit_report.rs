use anchor_lang::prelude::*;
use crate::state::{AgentProfile, NileAuthority, OracleReport};
use crate::errors::NileError;

#[derive(Accounts)]
#[instruction(program_address: Pubkey, event_type: String, headline: String, impact_score: i8)]
pub struct SubmitReport<'info> {
    #[account(
        init,
        payer = agent,
        space = 8 + OracleReport::INIT_SPACE,
        seeds = [
            b"report",
            program_address.as_ref(),
            &authority.total_reports.to_le_bytes(),
        ],
        bump,
    )]
    pub report: Account<'info, OracleReport>,

    #[account(
        mut,
        seeds = [b"agent", agent.key().as_ref()],
        bump = agent_profile.bump,
    )]
    pub agent_profile: Account<'info, AgentProfile>,

    #[account(
        mut,
        seeds = [b"nile_authority"],
        bump = authority.bump,
    )]
    pub authority: Account<'info, NileAuthority>,

    #[account(mut)]
    pub agent: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<SubmitReport>,
    program_address: Pubkey,
    event_type: String,
    headline: String,
    impact_score: i8,
) -> Result<()> {
    require!(event_type.len() <= 32, NileError::EventTypeTooLong);
    require!(headline.len() <= 200, NileError::HeadlineTooLong);
    require!(
        impact_score >= -100 && impact_score <= 100,
        NileError::ImpactOutOfRange
    );
    require!(ctx.accounts.agent_profile.is_active, NileError::AgentSuspended);

    let agent_count = ctx.accounts.authority.agent_count;
    let quorum = ((agent_count as u64 * 2 + 2) / 3) as u8; // ceil(2/3)

    let report = &mut ctx.accounts.report;
    report.program_address = program_address;
    report.submitter = ctx.accounts.agent.key();
    report.event_type = event_type;
    report.headline = headline;
    report.impact_score = impact_score;
    report.confirmations = 1; // Submitter auto-confirms
    report.rejections = 0;
    report.required_quorum = quorum.max(1);
    report.finalized = quorum <= 1; // Auto-finalize if only 1 agent
    report.accepted = quorum <= 1;
    report.submitted_at = Clock::get()?.unix_timestamp;
    report.finalized_at = 0;
    report.bump = ctx.bumps.report;

    // Update stats
    ctx.accounts.agent_profile.total_reports += 1;
    ctx.accounts.agent_profile.points += 5;
    ctx.accounts.authority.total_reports += 1;

    Ok(())
}
