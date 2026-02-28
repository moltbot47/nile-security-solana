use anchor_lang::prelude::*;
use crate::state::{AgentProfile, NileAuthority};

#[derive(Accounts)]
#[instruction(agent: Pubkey)]
pub struct AuthorizeAgent<'info> {
    #[account(
        mut,
        seeds = [b"nile_authority"],
        bump = authority.bump,
        has_one = admin,
    )]
    pub authority: Account<'info, NileAuthority>,

    #[account(
        init,
        payer = admin,
        space = 8 + AgentProfile::INIT_SPACE,
        seeds = [b"agent", agent.as_ref()],
        bump,
    )]
    pub agent_profile: Account<'info, AgentProfile>,

    #[account(mut)]
    pub admin: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<AuthorizeAgent>, agent: Pubkey) -> Result<()> {
    let authority = &mut ctx.accounts.authority;
    authority.agent_count += 1;

    let profile = &mut ctx.accounts.agent_profile;
    profile.agent_address = agent;
    profile.authorized_by = ctx.accounts.admin.key();
    profile.is_active = true;
    profile.total_scores = 0;
    profile.total_reports = 0;
    profile.total_votes = 0;
    profile.points = 0;
    profile.authorized_at = Clock::get()?.unix_timestamp;
    profile.bump = ctx.bumps.agent_profile;

    Ok(())
}
