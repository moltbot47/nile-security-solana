use anchor_lang::prelude::*;

#[error_code]
pub enum NileError {
    #[msg("Score must be between 0 and 100")]
    ScoreOutOfRange,

    #[msg("Impact score must be between -100 and 100")]
    ImpactOutOfRange,

    #[msg("Agent is not authorized")]
    UnauthorizedAgent,

    #[msg("Agent is suspended")]
    AgentSuspended,

    #[msg("Report is already finalized")]
    ReportAlreadyFinalized,

    #[msg("Agent has already voted on this report")]
    AlreadyVoted,

    #[msg("Program name too long (max 64 chars)")]
    NameTooLong,

    #[msg("Event type too long (max 32 chars)")]
    EventTypeTooLong,

    #[msg("Headline too long (max 200 chars)")]
    HeadlineTooLong,

    #[msg("Details URI too long (max 200 chars)")]
    DetailsTooLong,

    #[msg("Cannot vote on your own report")]
    SelfVoteNotAllowed,

    #[msg("Arithmetic overflow")]
    Overflow,
}
