use std::path::PathBuf;
use std::process::{Child, Command, Stdio};

pub fn start_python_service() -> std::io::Result<Child> {
    let mut ai_path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    ai_path.push("../ai");

    let mut bin = ai_path.join("dist/ai_service");
    if cfg!(windows) {
        bin.set_extension("exe");
    }

    if bin.exists() {
        Command::new(bin)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
    } else {
        Command::new("uvicorn")
            .current_dir(ai_path)
            .args(["main:app", "--host", "0.0.0.0", "--port", "8000"])
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
    }
}
