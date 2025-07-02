use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslIot, DslIotExpose, FerrumDsl};

use crate::ProjectPaths;

fn generate_gpio(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
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

fn generate_mqtt(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
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

fn generate_ethercat(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    fs::create_dir_all(&dir)?;
    let content = format!(
        "use ethercat_rs::Master;\n\npub fn {name}_master() -> Master {{\n    // \u{26F3} AI_FILL[iot_ethercat] --context=iot:{orig}\n    unimplemented!()\n}}\n",
        name = iot.name.to_snake_case(),
        orig = iot.name
    );
    fs::write(
        dir.join(format!("{}_ethercat.rs", iot.name.to_snake_case())),
        content,
    )?;
    Ok(())
}

pub fn generate_iot(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.rs", iot.name.to_snake_case()));
    fs::write(&file, &iot.code)?;

    if iot
        .protocol
        .as_deref()
        .map(|p| p.eq_ignore_ascii_case("gpio"))
        .unwrap_or(false)
        && iot
            .driver
            .as_deref()
            .map(|d| d.eq_ignore_ascii_case("rppal"))
            .unwrap_or(false)
    {
        generate_gpio(iot, paths)?;
    }

    if iot
        .protocol
        .as_deref()
        .map(|p| p.eq_ignore_ascii_case("mqtt"))
        .unwrap_or(false)
    {
        generate_mqtt(iot, paths)?;
    }

    if iot
        .protocol
        .as_deref()
        .map(|p| p.eq_ignore_ascii_case("ethercat"))
        .unwrap_or(false)
    {
        generate_ethercat(iot, paths)?;
    }

    if let Some(expose) = &iot.expose {
        generate_exposed(iot, expose, paths)?;
    }

    Ok(())
}

fn generate_exposed(iot: &DslIot, expose: &DslIotExpose, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    let method = expose.method.as_deref().unwrap_or("POST");
    let path = expose
        .path
        .clone()
        .unwrap_or_else(|| format!("/iot/{}", iot.name));
    let protocol = expose.protocol.as_deref().unwrap_or("http");

    if protocol.eq_ignore_ascii_case("mqtt") {
        let content = format!(
            "// MQTT template for {name}\n// Topic: {path}\n// \u{26F3} AI_FILL[iot_mqtt] --context=iot:{name}\n",
            name = iot.name,
            path = path
        );
        fs::write(
            dir.join(format!("{}_mqtt.rs", iot.name.to_snake_case())),
            content,
        )?;
    } else {
        let handler_name = format!("{}_handler", iot.name.to_snake_case());
        let content = format!(
            "use axum::{{Json, extract::State}};\nuse std::sync::Arc;\nuse crate::AppState;\n\npub async fn {handler_name}(State(_state): State<Arc<AppState>>) -> Json<()> {{\n    // Exposed via {method} {path}\n    // \u{26F3} AI_FILL[iot_http] --context=iot:{orig}\n    Json(())\n}}\n",
            handler_name = handler_name,
            method = method,
            path = path,
            orig = iot.name,
        );
        fs::write(dir.join(format!("{}.rs", handler_name)), content)?;
    }

    if expose.generate_hook {
        let hook_dir = paths.frontend.join("hooks");
        fs::create_dir_all(&hook_dir)?;
        let hook_name = iot.name.to_pascal_case();

        let content = if protocol.eq_ignore_ascii_case("mqtt") {
            format!(
                "import {{ useEffect }} from 'react';\nimport mqtt from 'mqtt';\n\nexport function use{hook_name}(onMessage: (msg: string) => void) {{\n  useEffect(() => {{\n    const client = mqtt.connect('ws://localhost:1884');\n    client.subscribe('{path}');\n    client.on('message', (_t, m) => onMessage(m.toString()));\n    return () => client.end();\n  }}, [onMessage]);\n}}\n",
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
    }

    Ok(())
}

pub fn compile_iot(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for i in &dsl.iot {
        generate_iot(i, paths)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn generate_iot_creates_file() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Blink".into(),
            code: "fn blink() {}".into(),
            protocol: None,
            driver: None,
            simulate: false,
            expose: None,
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/blink.rs").exists());
    }

    #[test]
    fn generate_iot_expose_http_creates_files() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Blink".into(),
            code: "fn blink() {}".into(),
            protocol: None,
            driver: None,
            simulate: false,
            expose: Some(DslIotExpose {
                method: Some("POST".into()),
                path: None,
                protocol: Some("http".into()),
                generate_hook: true,
                generate_component: false,
            }),
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/blink.rs").exists());
        assert!(dir.path().join("backend/iot/blink_handler.rs").exists());
        assert!(dir.path().join("frontend/hooks/useBlink.ts").exists());
    }

    #[test]
    fn generate_iot_expose_mqtt_creates_files() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Sensor".into(),
            code: "fn read() {}".into(),
            protocol: None,
            driver: None,
            simulate: false,
            expose: Some(DslIotExpose {
                method: None,
                path: Some("sensors/temp".into()),
                protocol: Some("mqtt".into()),
                generate_hook: true,
                generate_component: false,
            }),
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/sensor.rs").exists());
        assert!(dir.path().join("backend/iot/sensor_mqtt.rs").exists());
        assert!(dir.path().join("frontend/hooks/useSensor.ts").exists());
    }

    #[test]
    fn generate_iot_gpio_rppal_stub() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Blink".into(),
            code: "fn blink() {}".into(),
            protocol: Some("gpio".into()),
            driver: Some("rppal".into()),
            simulate: false,
            expose: None,
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/blink_gpio.rs").exists());
    }

    #[test]
    fn generate_iot_mqtt_stub() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Telem".into(),
            code: "fn run() {}".into(),
            protocol: Some("mqtt".into()),
            driver: None,
            simulate: false,
            expose: None,
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/telem_mqtt_client.rs").exists());
    }

    #[test]
    fn generate_iot_ethercat_stub() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Robot".into(),
            code: "fn run() {}".into(),
            protocol: Some("ethercat".into()),
            driver: None,
            simulate: false,
            expose: None,
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/robot_ethercat.rs").exists());
    }
}
