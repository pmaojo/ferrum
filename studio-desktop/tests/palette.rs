use studio_desktop::ui::palette::{NodeTemplates};

#[test]
fn default_templates_have_examples() {
    let templates = NodeTemplates::default();
    assert!(templates.0.iter().any(|t| t.label == "component"));
    assert!(templates.0.iter().any(|t| t.label == "service"));
}
