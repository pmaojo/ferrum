use bevy_egui::egui::Color32;
use studio_desktop::graph::Node as GraphNode;
use studio_desktop::ui::node_factory::{DefaultPalette, Palette};
use ferrum_shared_models::NodeType;

#[test]
fn default_palette_returns_type_colors() {
    let palette = DefaultPalette;
    let node = GraphNode {
        id: "iot".into(),
        node_type: NodeType::Iot,
        doc: None,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: Vec::new(),
        implements: None,
        view: None,
        schema: None,
        api_name: None,
        ref_node: None,
    };
    assert_eq!(
        palette.color(&node, false),
        Color32::from_rgb(250, 180, 100)
    );
    let node2 = GraphNode {
        id: "n".into(),
        node_type: NodeType::Component,
        doc: None,
        description: None,
        story: None,
        input: Vec::new(),
        output: None,
        depends_on: Vec::new(),
        implements: None,
        view: None,
        schema: None,
        api_name: None,
        ref_node: None,
    };
    assert_eq!(palette.color(&node2, true), Color32::LIGHT_BLUE);
}
