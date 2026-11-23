//! Compatibility facade for SoundCraft's sample-index time API in shared `craft-time`.
#![deny(clippy::unwrap_used, clippy::expect_used, clippy::panic, clippy::unimplemented, clippy::todo, clippy::unreachable)]

pub use craft_time::soundcraft::*;

#[cfg(test)]
extern crate self as soundcraft_time;
#[cfg(test)]
mod probe69 {
    mod history;
    mod history_budget_tests;
}
