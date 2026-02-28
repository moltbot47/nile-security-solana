use anchor_lang::prelude::*;
use crate::state::NileAuthority;

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = admin,
        space = 8 + NileAuthority::INIT_SPACE,
        seeds = [b"nile_authority"],
        bump,
    )]
    pub authority: Account<'info, NileAuthority>,

    #[account(mut)]
    pub admin: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<Initialize>) -> Result<()> {
    let authority = &mut ctx.accounts.authority;
    authority.version = 1;
    authority.admin = ctx.accounts.admin.key();
    authority.agent_count = 0;
    authority.total_scores_submitted = 0;
    authority.total_reports = 0;
    authority.bump = ctx.bumps.authority;
    Ok(())
}
