use ferrum_cli::commands::compile_with_formatters;
use std::fs;
use tempfile::tempdir;
use std::os::unix::fs::PermissionsExt;
use std::env;

struct TouchFormatter {
    path: std::path::PathBuf,
}

impl ferrum_compiler::FormatStep for TouchFormatter {
    fn run(&self, _dir: &std::path::Path) -> anyhow::Result<()> {
        fs::write(&self.path, b"called")?;
        Ok(())
    }
}

fn templates_path() -> std::path::PathBuf {
    std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("templates")
}

#[test]
fn compile_generates_files_and_formats() {
    let yaml = r#"module: test
nodes:
  - id: User
    type: entity
    input:
      - name: name
        type: string
"#;
    let tmp = tempdir().unwrap();
    let file = tmp.path().join("mod.yaml");
    fs::write(&file, yaml).unwrap();

    let out = tempdir().unwrap();

    // Provide dummy executables to capture formatter invocations
    let bin = tempdir().unwrap();
    let cargo_called = out.path().join("cargo_called");
    let prettier_called = out.path().join("prettier_called");
    fs::write(
        bin.path().join("cargo"),
        "#!/bin/sh\ntouch \"$MOCK_CARGO\"\n",
    )
    .unwrap();
    fs::set_permissions(bin.path().join("cargo"), fs::Permissions::from_mode(0o755)).unwrap();
    fs::write(
        bin.path().join("prettier"),
        "#!/bin/sh\ntouch \"$MOCK_PRETTIER\"\n",
    )
    .unwrap();
    fs::set_permissions(bin.path().join("prettier"), fs::Permissions::from_mode(0o755)).unwrap();

    env::set_var("MOCK_CARGO", &cargo_called);
    env::set_var("MOCK_PRETTIER", &prettier_called);
    let original_path = env::var("PATH").unwrap();
    env::set_var(
        "PATH",
        format!("{}:{}", bin.path().display(), original_path),
    );

    let rust_log = out.path().join("rust_fmt");
    let ts_log = out.path().join("ts_fmt");
    let rust_fmt = TouchFormatter { path: rust_log.clone() };
    let ts_fmt = TouchFormatter { path: ts_log.clone() };

    compile_with_formatters(
        vec![file.to_string_lossy().to_string()],
        Some(out.path().to_path_buf()),
        Some(templates_path()),
        None,
        false,
        &rust_fmt,
        &ts_fmt,
    )
    .unwrap();

    env::set_var("PATH", original_path);

    assert!(cargo_called.exists());
    assert!(prettier_called.exists());

    assert!(out.path().join("shared-models/user.rs").exists());
    assert!(rust_log.exists());
    assert!(ts_log.exists());
}
