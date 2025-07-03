use bevy::prelude::*;
use leafwing_input_manager::prelude::*;

#[derive(Actionlike, PartialEq, Eq, Hash, Clone, Copy, Debug, Reflect)]
pub enum Action {
    #[actionlike(Button)]
    Pan,
    #[actionlike(Axis)]
    Zoom,
    #[actionlike(Button)]
    Select,
}

impl Action {
    pub fn input_map() -> InputMap<Self> {
        InputMap::default()
            .with(Action::Pan, MouseButton::Left)
            .with_axis(Action::Zoom, MouseScrollAxis::Y)
            .with(Action::Select, MouseButton::Left)
    }
}

pub fn spawn_input(mut commands: Commands) {
    commands.spawn(InputManagerBundle::<Action>::with_map(Action::input_map()));
}
