use studio_desktop::settings::ProjectSettings;

#[test]
fn default_settings() {
    let settings = ProjectSettings::default();
    assert_eq!(settings.grafo_path, "grafo.yaml");
    assert!(!settings.confirmed);
}
