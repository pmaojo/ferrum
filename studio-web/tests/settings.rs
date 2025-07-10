use studio_web::settings::{MemoryStore, Settings, SettingsStore, Theme};

#[test]
fn default_load_returns_default_settings() {
    let store = MemoryStore::default();
    let loaded = store.load().expect("load");
    assert_eq!(loaded, Settings::default());
}

#[test]
fn saves_and_loads_settings() {
    let store = MemoryStore::default();
    let mut s = Settings::default();
    s.layout = Some("layout".into());
    s.theme = Theme::Dark;
    store.save(&s).expect("save");

    let loaded = store.load().expect("load");
    assert_eq!(loaded, s);
}
