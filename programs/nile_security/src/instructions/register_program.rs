use anchor_lang::prelude::*;
use crate::state::ProgramProfile;
use crate::errors::NileError;

#[derive(Accounts)]
#[instruction(program_address: Pubkey, name: String)]
pub struct RegisterProgram<'info> {
    #[account(
        init,
        payer = registrant,
        space = 8 + ProgramProfile::INIT_SPACE,
        seeds = [b"program", program_address.as_ref()],
        bump,
    )]
    pub profile: Account<'info, ProgramProfile>,

    #[account(mut)]
    pub registrant: Signer<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(
    ctx: Context<RegisterProgram>,
    program_address: Pubkey,
    name: String,
) -> Result<()> {
    require!(name.len() <= 64, NileError::NameTooLong);

    let profile = &mut ctx.accounts.profile;
    profile.program_address = program_address;
    profile.name = name;
    profile.registrant = ctx.accounts.registrant.key();

    // Initialize scores to 0 (unscored)
    profile.name_score = 0;
    profile.image_score = 0;
    profile.likeness_score = 0;
    profile.essence_score = 0;
    profile.total_score = 0;
    profile.grade = "F".to_string();

    profile.score_count = 0;
    profile.last_scored_at = 0;
    profile.registered_at = Clock::get()?.unix_timestamp;
    profile.details_uri = String::new();
    profile.bump = ctx.bumps.profile;

    Ok(())
}
