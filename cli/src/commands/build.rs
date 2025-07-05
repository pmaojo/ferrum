use anyhow::Result;

pub fn build(target: Option<String>) -> Result<()> {
    use std::process::Command;
    use std::path::Path;

    let mut cmd = Command::new("cargo");
    cmd.arg("build")
        .arg("--manifest-path")
        .arg("backend/Cargo.toml");

    if let Some(t) = target {
        let triple = match t.as_str() {
            "rpi" => "armv7-unknown-linux-gnueabihf",
            "thumbv7em" => "thumbv7em-none-eabi",
            other => other,
        };

        ensure_rust_target(triple)?;
        cmd.arg("--target").arg(triple);
    }

    let status = cmd.status()?;
    if !status.success() {
        anyhow::bail!("Cargo build failed");
    }
    if Path::new("frontend_leptos").exists() {
        let status = Command::new("cargo")
            .args(["leptos", "build", "--release"])
            .current_dir("frontend_leptos")
            .status()?;
        if !status.success() {
            anyhow::bail!("cargo-leptos build failed");
        }
    }
    println!("✅ Build finished");
    Ok(())
}

fn ensure_rust_target(triple: &str) -> Result<()> {
    use std::process::Command;

    let list = Command::new("rustup")
        .args(["target", "list", "--installed"])
        .output()?;
    let installed = String::from_utf8_lossy(&list.stdout);

    if !installed.lines().any(|l| l.trim() == triple) {
        let status = Command::new("rustup")
            .args(["target", "add", triple])
            .status()?;
        if !status.success() {
            anyhow::bail!("Failed to add target {triple}");
        }
    }
    Ok(())
}

