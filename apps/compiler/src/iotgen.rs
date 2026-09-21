use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslIot, FerrumDsl};

use crate::iot_protocol::{DefaultProtocol, EthercatProtocol, GpioProtocol, IotProtocol, MqttProtocol};
use crate::ProjectPaths;

fn generate_simulator(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot/sim");
    fs::create_dir_all(&dir)?;
    let content = format!(
        "pub fn {name}_sim() {{\n    println!(\"[SIM] {orig} driver\");\n}}\n",
        name = iot.name.to_snake_case(),
        orig = iot.name
    );
    fs::write(dir.join(format!("{}_sim.rs", iot.name.to_snake_case())), content)?;
    Ok(())
}

pub fn generate_iot(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.rs", iot.name.to_snake_case()));
    fs::write(&file, &iot.code)?;

    let protocol: Box<dyn IotProtocol> = match iot.protocol.as_deref() {
        Some(p) if p.eq_ignore_ascii_case("gpio")
            && iot
                .driver
                .as_deref()
                .map(|d| d.eq_ignore_ascii_case("rppal"))
                .unwrap_or(false) => Box::new(GpioProtocol),
        Some(p) if p.eq_ignore_ascii_case("mqtt") => Box::new(MqttProtocol),
        Some(p) if p.eq_ignore_ascii_case("ethercat") => Box::new(EthercatProtocol),
        _ => Box::new(DefaultProtocol),
    };

    protocol.generate_driver(iot, paths)?;

    if let Some(expose) = &iot.expose {
        protocol.generate_handler(iot, expose, paths)?;
        if expose.generate_hook {
            protocol.generate_hook(iot, expose, paths)?;
        }
    }

    Ok(())
}


pub fn compile_iot(dsl: &FerrumDsl, paths: &ProjectPaths) -> Result<()> {
    for i in &dsl.iot {
        generate_iot(i, paths)?;
        if i.simulate {
            generate_simulator(i, paths)?;
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use ferrum_shared_models::DslIotExpose;
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

    #[test]
    fn ethercat_stub_compiles() {
        use std::process::Command;

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

        let stub_dir = dir.path().join("stub");
        fs::create_dir(&stub_dir).unwrap();
        fs::write(
            stub_dir.join("lib.rs"),
            "pub struct Master; impl Default for Master { fn default() -> Self { Self } }",
        )
        .unwrap();
        let stub_rlib = stub_dir.join("libethercat_rs.rlib");
        let status = Command::new("rustc")
            .args(["--crate-type", "lib", "lib.rs", "-o"])
            .arg(&stub_rlib)
            .current_dir(&stub_dir)
            .status()
            .unwrap();
        assert!(status.success());

        let gen_file = dir.path().join("backend/iot/robot_ethercat.rs");
        let status = Command::new("rustc")
            .args(["--edition", "2021", "--crate-type", "lib"])
            .arg(&gen_file)
            .arg("--extern")
            .arg(format!("ethercat_rs={}", stub_rlib.display()))
            .status()
            .unwrap();
        assert!(status.success());
    }

    #[test]
    fn generate_simulator_creates_file() {
        let dir = tempdir().unwrap();
        let paths = ProjectPaths::new(dir.path());
        let iot = DslIot {
            name: "Blink".into(),
            code: "fn blink() {}".into(),
            protocol: None,
            driver: None,
            simulate: true,
            expose: None,
        };
        generate_simulator(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/sim/blink_sim.rs").exists());
    }
}
