use super::Plugin;

/// Stub plugin for Stripe payments.
pub struct StripePlugin;

impl Plugin for StripePlugin {
    fn name(&self) -> &'static str {
        "stripe"
    }
}
