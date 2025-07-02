use std::collections::BTreeMap;
use anyhow::Result;
use ferrum_engine::plugins::Plugin;
use ferrum_shared_models::{DslIot, DslIotExpose, DslResource, FerrumDsl};

/// Plugin that injects sample IoT drivers and a telemetry resource.
pub struct IotBasicPlugin;

impl Plugin for IotBasicPlugin {
    fn name(&self) -> &'static str { "iot-basic" }

    fn extend_dsl(&self, dsl: &mut FerrumDsl) -> Result<()> {
        if !dsl.app.features.contains(&"mqtt".to_string()) {
            dsl.app.features.push("mqtt".to_string());
        }

        if !dsl.resources.iter().any(|r| r.name == "telemetry") {
            dsl.resources.push(DslResource {
                name: "telemetry".to_string(),
                resource_type: "mqtt".to_string(),
                config: BTreeMap::new(),
            });
        }

        if !dsl.iot.iter().any(|i| i.name == "read_temperature") {
            dsl.iot.push(DslIot {
                name: "read_temperature".to_string(),
                code: "pub fn read_temperature() -> f32 { 0.0 }".to_string(),
                protocol: None,
                driver: None,
                simulate: true,
                expose: Some(DslIotExpose {
                    method: Some("GET".to_string()),
                    path: Some("/sensors/temp".to_string()),
                    protocol: Some("http".to_string()),
                    generate_hook: true,
                    generate_component: true,
                }),
            });
        }

        if !dsl.iot.iter().any(|i| i.name == "read_humidity") {
            dsl.iot.push(DslIot {
                name: "read_humidity".to_string(),
                code: "pub fn read_humidity() -> f32 { 0.0 }".to_string(),
                protocol: None,
                driver: None,
                simulate: true,
                expose: Some(DslIotExpose {
                    method: Some("GET".to_string()),
                    path: Some("/sensors/humidity".to_string()),
                    protocol: Some("http".to_string()),
                    generate_hook: true,
                    generate_component: true,
                }),
            });
        }

        Ok(())
    }
}

#[no_mangle]
pub extern "C" fn plugin_create() -> Box<dyn Plugin> {
    Box::new(IotBasicPlugin)
}
