use bevy_egui::egui::Color32;
use studio_desktop::graph::Node;
use studio_desktop::ui::node_factory::{DefaultPalette, Palette};

#[test]
fn default_palette_returns_type_colors() {
    let palette = DefaultPalette;
    let node = Node {
        name: "iot".into(),
        node_type: Some("iot".into()),
        description: None,
        story: None,
        calls: None,
        used_by: None,
    };
    assert_eq!(
        palette.color(&node, false),
        Color32::from_rgb(250, 180, 100)
    );
    let node2 = Node {
        name: "n".into(),
        node_type: None,
        description: None,
        story: None,
        calls: None,
        used_by: None,
    };
    assert_eq!(palette.color(&node2, true), Color32::LIGHT_BLUE);
}
