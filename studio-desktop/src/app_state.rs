use bevy::prelude::States;

#[derive(States, Debug, Clone, Eq, PartialEq, Hash)]
pub enum AppState {
    Loading,
    InGame,
    Paused,
}

impl Default for AppState {
    fn default() -> Self {
        AppState::Loading
    }
}
