use anyhow::Result;
use inflector::Inflector;
use std::fs;

use ferrum_shared_models::{DslIot, FerrumDsl};

use crate::ProjectPaths;

pub fn generate_iot(iot: &DslIot, paths: &ProjectPaths) -> Result<()> {
    let dir = paths.backend.join("iot");
    fs::create_dir_all(&dir)?;
    let file = dir.join(format!("{}.rs", iot.name.to_snake_case()));
    fs::write(file, &iot.code)?;
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
        };
        generate_iot(&iot, &paths).unwrap();
        assert!(dir.path().join("backend/iot/blink.rs").exists());
    }
}
