use anyhow::Result;
use super::compile;

pub fn dev(docker: bool, with_graph: bool, with_ai: bool) -> Result<()> {
    use std::path::Path;
    use std::process::{Command, Stdio};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Arc;

    println!("🚀 Starting Ferrum development environment");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    let frontend_exists = Path::new("frontend").exists();

    if !docker {
        // Run local cargo and vite processes in parallel
        // Compile all YAML files first to ensure routes and types are up to date
        if let Ok(entries) = std::fs::read_dir("gen") {
            for entry in entries.flatten() {
                if entry.path().extension().and_then(|s| s.to_str()) == Some("yaml") {
                    let _ = compile(vec![entry.path().to_string_lossy().into()], None, None, None, false);
                }
            }
        }

        let mut backend = Command::new("cargo")
            .arg("run")
            .arg("--manifest-path")
            .arg("backend/Cargo.toml")
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()?;
        let mut frontend = if frontend_exists {
            Some(
                Command::new("npm")
                    .args(["run", "dev", "--prefix", "frontend"])
                    .stdout(Stdio::inherit())
                    .stderr(Stdio::inherit())
                    .spawn()?,
            )
        } else {
            None
        };

        let running = Arc::new(AtomicBool::new(true));
        let r = running.clone();
        ctrlc::set_handler(move || {
            r.store(false, Ordering::SeqCst);
        })?;

        while running.load(Ordering::SeqCst) {
            std::thread::sleep(std::time::Duration::from_millis(500));
            if backend.try_wait()?.is_some()
                || frontend.as_mut().and_then(|f| f.try_wait().ok()).is_some()
            {
                running.store(false, Ordering::SeqCst);
            }
        }

        let _ = backend.kill();
        if let Some(mut f) = frontend {
            let _ = f.kill();
        }
        return Ok(());
    }

    // Create a docker-compose command with the appropriate services
    let mut services = vec!["backend", "db"];
    if frontend_exists {
        services.insert(1, "frontend");
    }

    if with_graph {
        services.push("graphdb");
        println!("🔍 Including graph database (Neo4j)");
    }

    if with_ai {
        services.push("llm");
        println!("🧠 Including AI/LLM service (Ollama)");
    }

    println!("⚙️  Starting services: {}", services.join(", "));
    println!();

    // Build the docker-compose command
    let services_arg = services.join(" ");
    let docker_compose_cmd = format!("docker-compose up {}", services_arg);

    println!("🚀 Launching development environment...");
    println!("💡 Press Ctrl+C to stop all services");
    println!();

    // Execute the command
    let status = Command::new("sh")
        .arg("-c")
        .arg(&docker_compose_cmd)
        .status()?;

    if !status.success() {
        println!("❌ Failed to start development environment");
        return Err(anyhow::anyhow!("Docker command failed"));
    }

    Ok(())
}

