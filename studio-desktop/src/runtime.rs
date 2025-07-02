use bevy::prelude::Resource;
use std::sync::Arc;
use tokio::runtime::Runtime;

#[derive(Resource, Clone)]
pub struct AsyncRuntime(pub Arc<Runtime>);
