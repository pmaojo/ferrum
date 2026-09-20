use anyhow::Result;
use std::path::PathBuf;
use super::plugin_docs;

pub fn add_plugin(plugin: String) -> Result<()> {
    use std::fs::{self, OpenOptions};
    use std::io::Write;
    use std::path::Path;
    use std::process::Command;

    let dir = PathBuf::from(".ferrum");
    fs::create_dir_all(&dir)?;
    let file_path = dir.join("plugins.txt");
    let mut plugins = if file_path.exists() {
        fs::read_to_string(&file_path)?
            .lines()
            .map(|s| s.to_string())
            .collect::<Vec<_>>()
    } else {
        Vec::new()
    };

    let mut entry = plugin.clone();

    if plugin.starts_with("http") || (plugin.contains('/') && !Path::new(&plugin).exists()) {
        // Install from a remote git repository
        let repo_url = if plugin.starts_with("http") {
            plugin.clone()
        } else {
            format!("https://github.com/{}.git", plugin)
        };
        let repo_name = plugin.split('/').last().unwrap().trim_end_matches(".git");
        let dest = dir.join(repo_name);
        if !dest.exists() {
            println!("📥 Cloning {repo_url}...");
            let status = Command::new("git")
                .arg("clone")
                .arg(&repo_url)
                .arg(&dest)
                .status()?;
            if !status.success() {
                println!("Failed to clone repository");
            }
        }
        entry = dest.to_string_lossy().into_owned();
    } else if Path::new(&plugin).exists() {
        // Local path
        entry = std::fs::canonicalize(&plugin)?
            .to_string_lossy()
            .into_owned();
    }

    if !plugins.contains(&entry) {
        plugins.push(entry.clone());
        let mut f = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(&file_path)?;
        writeln!(f, "{}", plugins.join("\n"))?;
        println!("✅ Added plugin: {}", entry);

        // Automatically compile if Cargo.toml exists
        let cargo_path = Path::new(&entry).join("Cargo.toml");
        if cargo_path.exists() {
            println!("🔨 Building plugin...");
            let status = Command::new("cargo")
                .arg("build")
                .arg("--release")
                .current_dir(&entry)
                .status()?;
            if status.success() {
                println!("✅ Plugin compiled");
                // Show SHA256 of compiled library if plugin.toml defines it
                let meta = Path::new(&entry).join("plugin.toml");
                if let Ok(meta) = ferrum_engine::plugins::PluginMetadata::from_file(&meta) {
                    let lib_path = Path::new(&entry).join(&meta.library);
                    if lib_path.exists() {
                        if let Ok(bytes) = std::fs::read(&lib_path) {
                            use sha2::{Digest, Sha256};
                            let hash = Sha256::digest(&bytes);
                            let hex: String = hash.iter().map(|b| format!("{b:02x}")).collect();
                            println!("🔑 SHA256: {hex}");
                        }
                    }
                }
            } else {
                println!("⚠️ Failed to compile plugin");
            }
        } else {
            let meta = Path::new(&entry).join("plugin.toml");
            if meta.exists() {
                println!("⚠️ Using precompiled plugin binary. Ensure you trust the source.");
            }
        }

        // show docs if available
        if let Ok(_) = plugin_docs(entry.clone()) {}
    } else {
        println!("Plugin '{}' already added", entry);
    }
    Ok(())
}

/// Remove a plugin from the .ferrum/plugins list.
pub fn remove_plugin(plugin: String) -> Result<()> {
    use std::fs;

    let file_path = PathBuf::from(".ferrum/plugins.txt");
    if !file_path.exists() {
        println!("No plugins installed.");
        return Ok(());
    }

    let mut plugins: Vec<String> = fs::read_to_string(&file_path)?
        .lines()
        .map(|s| s.to_string())
        .collect();

    if let Some(pos) = plugins.iter().position(|p| p == &plugin) {
        plugins.remove(pos);
        if plugins.is_empty() {
            fs::remove_file(&file_path)?;
        } else {
            fs::write(&file_path, plugins.join("\n"))?;
        }
        println!("✅ Removed plugin: {}", plugin);
    } else {
        println!("Plugin '{}' not found", plugin);
    }
    Ok(())
}

/// List installed plugins from .ferrum/plugins.
pub fn list_plugins() -> Result<()> {
    use std::fs;
    let file_path = PathBuf::from(".ferrum/plugins.txt");
    if file_path.exists() {
        let contents = fs::read_to_string(file_path)?;
        if contents.trim().is_empty() {
            println!("No plugins installed.");
        } else {
            println!("Installed plugins:");
            for p in contents.lines() {
                println!("- {}", p);
            }
        }
    } else {
        println!("No plugins installed.");
    }
    Ok(())
}

