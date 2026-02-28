use anchor_lang::prelude::*;
use crate::state::{AgentProfile, NileAuthority, ProgramProfile};
use crate::errors::NileError;

#[derive(Accounts)]
pub struct SubmitScore<'info> {
    #[account(
        mut,
        seeds = [b"program", profile.program_address.as_ref()],
        bump = profile.bump,
    )]
    pub profile: Account<'info, ProgramProfile>,

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

    pub agent: Signer<'info>,
}

pub fn handler(
    ctx: Context<SubmitScore>,
    name_score: u8,
    image_score: u8,
    likeness_score: u8,
    essence_score: u8,
    details_uri: String,
) -> Result<()> {
    // Validate scores
    require!(name_score <= 100, NileError::ScoreOutOfRange);
    require!(image_score <= 100, NileError::ScoreOutOfRange);
    require!(likeness_score <= 100, NileError::ScoreOutOfRange);
    require!(essence_score <= 100, NileError::ScoreOutOfRange);
    require!(details_uri.len() <= 200, NileError::DetailsTooLong);

    // Verify agent is active
    require!(ctx.accounts.agent_profile.is_active, NileError::AgentSuspended);

    // Compute weighted total (25% each)
    let total = (name_score as u16 + image_score as u16
        + likeness_score as u16 + essence_score as u16) / 4;
    let total = total as u8;

    let grade = match total {
        90..=100 => "A+",
        80..=89 => "A",
        70..=79 => "B",
        60..=69 => "C",
        50..=59 => "D",
        _ => "F",
    };

    // Update profile
    let profile = &mut ctx.accounts.profile;
    profile.name_score = name_score;
    profile.image_score = image_score;
    profile.likeness_score = likeness_score;
    profile.essence_score = essence_score;
    profile.total_score = total;
    profile.grade = grade.to_string();
    profile.score_count += 1;
    profile.last_scored_at = Clock::get()?.unix_timestamp;
    profile.details_uri = details_uri;

    // Update agent stats
    ctx.accounts.agent_profile.total_scores += 1;
    ctx.accounts.agent_profile.points += 10; // 10 points per score submission

    // Update global stats
    ctx.accounts.authority.total_scores_submitted += 1;

    Ok(())
}
