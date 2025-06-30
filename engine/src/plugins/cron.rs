use super::Plugin;

/// Stub plugin providing cron job support.
pub struct CronPlugin;

impl Plugin for CronPlugin {
    fn name(&self) -> &'static str {
        "cron"
    }
}
