use anyhow::Result;
use std::{fs, path::Path};

pub fn copy_if_missing<P: AsRef<Path>>(contents: &str, dest: P) -> Result<()> {
    let dest = dest.as_ref();
    if dest.exists() {
        return Ok(());
    }
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(dest, contents)?;
    Ok(())
}

pub fn ensure_env_var(var_name: &str, var_value: &str) -> Result<()> {
    let path = Path::new(".env");
    let mut content = fs::read_to_string(path).unwrap_or_default();

    if !content.contains(var_name) {
        content.push_str(&format!("\n{}={}", var_name, var_value));
        fs::write(path, content.trim_start())?;
    }
    Ok(())
}

pub fn ensure_dep(dep: &str, version: &str) -> Result<()> {
    use std::fs::OpenOptions;
    use std::io::Write;

    let path = Path::new("backend/Cargo.toml");
    if !path.exists() {
        return Ok(());
    }
    let contents = fs::read_to_string(path)?;
    if !contents.contains(dep) {
        let mut f = OpenOptions::new().append(true).open(path)?;
        writeln!(f, "{dep} = \"{version}\"")?;
    }
    Ok(())
}
