use bevy::prelude::*;
use leafwing_input_manager::prelude::*;
use studio_desktop::input::{spawn_input, Action};

#[test]
fn spawn_input_adds_bundle() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .add_plugins(bevy::input::InputPlugin)
        .add_plugins(InputManagerPlugin::<Action>::default())
        .add_systems(Startup, spawn_input);
    app.update();

    let mut query = app
        .world_mut()
        .query::<(&ActionState<Action>, &InputMap<Action>)>();
    let count = query.iter(&app.world()).count();
    assert_eq!(count, 1);
}

#[test]
fn input_map_contains_pan() {
    let map = Action::input_map();
    assert!(map.get(&Action::Pan).is_some());
}

#[test]
fn input_map_contains_start_drag() {
    let map = Action::input_map();
    assert!(map.get(&Action::StartDrag).is_some());
    assert!(map.get(&Action::Drop).is_some());
}
