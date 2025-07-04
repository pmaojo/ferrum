use bevy::prelude::*;
use bevy_egui::egui;
use studio_desktop::graph::{GraphData, NodePositions, Viewport};
use studio_desktop::ui::palette::{handle_drop, NodeTemplate};
use studio_desktop::ui::UiState;

#[test]
fn dropping_template_creates_node() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins)
        .init_resource::<GraphData>()
        .init_resource::<NodePositions>()
        .init_resource::<Viewport>()
        .init_resource::<UiState>();

    let rect = egui::Rect::from_min_size(egui::pos2(0.0, 0.0), egui::vec2(400.0, 400.0));

    // prepare drag from palette
    {
        let mut state = app.world_mut().resource_mut::<UiState>();
        state.palette_dragging = Some(NodeTemplate {
            label: "service".into(),
            node_type: Some("service".into()),
        });
    }

    let ctx = egui::Context::default();
    let pos = egui::pos2(100.0, 120.0);
    let mut input = egui::RawInput::default();
    input.events.push(egui::Event::PointerMoved(pos));
    input.events.push(egui::Event::PointerButton {
        pos,
        button: egui::PointerButton::Primary,
        pressed: false,
        modifiers: egui::Modifiers::NONE,
    });
    ctx.begin_frame(input);

    {
        let viewport = app.world().resource::<Viewport>().clone();
        let mut world = app.world_mut();
        let mut state = world.resource_mut::<UiState>();
        let mut data = world.resource_mut::<GraphData>();
        let mut positions = world.resource_mut::<NodePositions>();
        handle_drop(&ctx, rect, &viewport, &mut state, &mut data, &mut positions);
    }
    ctx.end_frame();

    let data = app.world().resource::<GraphData>();
    let positions = app.world().resource::<NodePositions>();
    assert_eq!(data.nodes.len(), 1);
    let id = &data.nodes[0].id;
    assert!(positions.0.contains_key(id));
}
