use super::Plugin;

/// Stub plugin for Sanity CMS integration.
pub struct CmsSanityPlugin;

impl Plugin for CmsSanityPlugin {
    fn name(&self) -> &'static str {
        "cms-sanity"
    }
}
