use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslIot, DslIotExpose};

use crate::ProjectPaths;

/// Abstraction over IoT protocol specific code generation.
///
/// Each protocol can customize how driver stubs, frontend hooks
/// and HTTP/MQTT handlers are generated.
pub trait IotProtocol {
    /// Generate backend driver code for the IoT module.
    fn generate_driver(&self, iot: &DslIot, paths: &ProjectPaths) -> Result<()>;
    /// Generate a frontend hook for the exposed IoT API.
    fn generate_hook(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()>;
    /// Generate a backend handler for the exposed IoT API.
    fn generate_handler(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()>;
}

fn default_generate_hook(iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
    let hook_dir = paths.frontend.join("hooks");
    fs::create_dir_all(&hook_dir)?;
    let method = expose.method.as_deref().unwrap_or("POST");
    let path = expose
        .path
        .clone()
        .unwrap_or_else(|| format!("/iot/{}", iot.name));
    let protocol = expose.protocol.as_deref().unwrap_or("http");
    let hook_name = iot.name.to_pascal_case();

    let content = if protocol.eq_ignore_ascii_case("mqtt") {
        format!(
            "import {{ useEffect }} from 'react';\nimport mqtt from 'mqtt';\n\nexport function use{hook_name}(onMessage: (msg: string) => void) {{\n  useEffect(() => {{\n    const client = mqtt.connect('ws://localhost:1884');\n    client.subscribe('{path}');\n    client.on('message', (_t, m) => onMessage(m.to_string()));\n    return () => client.end();\n  }}, [onMessage]);\n}}\n",
            hook_name = hook_name,
            path = path
        )
    } else {
        format!(
            "import {{ useState }} from 'react';\n\nexport function use{hook_name}() {{\n  const [isLoading, setLoading] = useState(false);\n  const mutate = async () => {{\n    setLoading(true);\n    await fetch('{path}', {{ method: '{method}' }});\n    setLoading(false);\n  }};\n  return {{ mutate, isLoading }};\n}}\n",
            hook_name = hook_name,
            path = path,
            method = method
        )
    };

    fs::write(hook_dir.join(format!("use{hook_name}.ts")), content)?;
    Ok(())
}

fn default_generate_handler(iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    let method = expose.method.as_deref().unwrap_or("POST");
    let path = expose
        .path
        .clone()
        .unwrap_or_else(|| format!("/iot/{}", iot.name));
    let protocol = expose.protocol.as_deref().unwrap_or("http");

    if protocol.eq_ignore_ascii_case("mqtt") {
        let content = if iot.simulate {
            format!(
                "pub fn {name}_mqtt() {{\n    super::sim::{name}_sim();\n}}\n",
                name = iot.name.to_snake_case()
            )
        } else {
            format!(
                "// MQTT template for {name}\n// Topic: {path}\n// \u{26F3} AI_FILL[iot_mqtt] --context=iot:{name}\n",
                name = iot.name,
                path = path
            )
        };
        fs::write(dir.join(format!("{}_mqtt.rs", iot.name.to_snake_case())), content)?;
    } else {
        let handler_name = format!("{}_handler", iot.name.to_snake_case());
        let content = if iot.simulate {
            format!(
                "use axum::{{Json, extract::State}};\nuse std::sync::Arc;\nuse crate::AppState;\n\npub async fn {handler_name}(State(_state): State<Arc<AppState>>) -> Json<()> {{\n    super::sim::{sim_fn}();\n    Json(())\n}}\n",
                handler_name = handler_name,
                sim_fn = format!("{}_sim", iot.name.to_snake_case())
            )
        } else {
            format!(
                "use axum::{{Json, extract::State}};\nuse std::sync::Arc;\nuse crate::AppState;\n\npub async fn {handler_name}(State(_state): State<Arc<AppState>>) -> Json<()> {{\n    // Exposed via {method} {path}\n    // \u{26F3} AI_FILL[iot_http] --context=iot:{orig}\n    Json(())\n}}\n",
                handler_name = handler_name,
                method = method,
                path = path,
                orig = iot.name,
            )
        };
        fs::write(dir.join(format!("{}.rs", handler_name)), content)?;
    }

    Ok(())
}

pub struct GpioProtocol;
impl IotProtocol for GpioProtocol {
    fn generate_driver(&self, iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
        let dir = paths.backend.join("iot");
        fs::create_dir_all(&dir)?;
        let content = format!(
            "use rppal::gpio::Gpio;\n\npub fn {name}_gpio() -> Gpio {{\n    // \u{26F3} AI_FILL[iot_gpio] --context=iot:{orig}\n    Gpio::new().unwrap()\n}}\n",
            name = iot.name.to_snake_case(),
            orig = iot.name
        );
        fs::write(dir.join(format!("{}_gpio.rs", iot.name.to_snake_case())), content)?;
        Ok(())
    }

    fn generate_hook(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_hook(iot, expose, paths)
    }

    fn generate_handler(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_handler(iot, expose, paths)
    }
}

pub struct MqttProtocol;
impl IotProtocol for MqttProtocol {
    fn generate_driver(&self, iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
        let dir = paths.backend.join("iot");
        fs::create_dir_all(&dir)?;
        let content = format!(
            "use rumqttc::{{MqttOptions, Client}};\n\npub fn {name}_mqtt_client() -> Client {{\n    let options = MqttOptions::new(\"{client}\", \"localhost\", 1883);\n    // \u{26F3} AI_FILL[iot_mqtt_client] --context=iot:{orig}\n    Client::new(options, 10)\n}}\n",
            name = iot.name.to_snake_case(),
            client = iot.name.to_snake_case(),
            orig = iot.name
        );
        fs::write(
            dir.join(format!("{}_mqtt_client.rs", iot.name.to_snake_case())),
            content,
        )?;
        Ok(())
    }

    fn generate_hook(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_hook(iot, expose, paths)
    }

    fn generate_handler(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_handler(iot, expose, paths)
    }
}

pub struct EthercatProtocol;
impl IotProtocol for EthercatProtocol {
    fn generate_driver(&self, iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
        let dir = paths.backend.join("iot");
        fs::create_dir_all(&dir)?;
        let content = format!(
            "use ethercat_rs::Master;\n\npub fn {name}_master() -> Master {{\n    // \u{26F3} AI_FILL[iot_ethercat] --context=iot:{orig}\n    Master::default()\n}}\n",
            name = iot.name.to_snake_case(),
            orig = iot.name
        );
        fs::write(
            dir.join(format!("{}_ethercat.rs", iot.name.to_snake_case())),
            content,
        )?;
        Ok(())
    }

    fn generate_hook(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_hook(iot, expose, paths)
    }

    fn generate_handler(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_handler(iot, expose, paths)
    }
}

pub struct DefaultProtocol;
impl IotProtocol for DefaultProtocol {
    fn generate_driver(&self, _iot: &DslIot, _paths: &ProjectPaths) -> Result<()> {
        Ok(())
    }

    fn generate_hook(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_hook(iot, expose, paths)
    }

    fn generate_handler(&self, iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
        default_generate_handler(iot, expose, paths)
    }
}
