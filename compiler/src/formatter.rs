use anyhow::{anyhow, Context, Result};
use std::path::Path;
use std::process::Command;

/// Abstraction over formatting steps that spawn external commands.
///
/// Implementations should be side-effect free except for running the
/// formatter process and modifying files in `dir`.
/// This allows unit tests to provide mock implementations.
pub trait FormatStep {
    /// Execute the formatting command for the given directory.
    ///
    /// Side effects:
    /// - Spawns an external process.
    /// - May rewrite files inside `dir`.
    fn run(&self, dir: &Path) -> Result<()>;
}

/// `cargo fmt` formatter implementation.
#[derive(Default)]
pub struct CargoFmt;

impl FormatStep for CargoFmt {
    fn run(&self, dir: &Path) -> Result<()> {
        let status = Command::new("cargo")
            .arg("fmt")
            .current_dir(dir)
            .status()
            .context("failed to execute 'cargo fmt'")?;
        if status.success() {
            Ok(())
        } else {
            Err(anyhow!("'cargo fmt' exited with an error"))
        }
    }
}

/// `prettier` formatter implementation.
#[derive(Default)]
pub struct Prettier;

impl FormatStep for Prettier {
    fn run(&self, dir: &Path) -> Result<()> {
        let status = Command::new("prettier")
            .arg("--write")
            .arg(dir)
            .status()
            .context("failed to execute 'prettier'")?;
        if status.success() {
            Ok(())
        } else {
            Err(anyhow!("'prettier' exited with an error"))
        }
    }
}

/// Format Rust sources in `dir` using the provided formatter.
///
/// Side effects: runs the formatter process and modifies sources in-place.
/// Prints a warning when the formatter is unavailable or fails.
pub fn format_rust(step: &dyn FormatStep, dir: &Path) {
    if let Err(e) = step.run(dir) {
        println!("⚠️  'cargo fmt' failed or is unavailable ({})", e);
    }
}

/// Format frontend sources using the provided formatter.
///
/// Side effects: runs the formatter process and modifies sources in-place.
/// Prints a warning when the formatter is unavailable or fails.
pub fn format_frontend(step: &dyn FormatStep, dir: &Path) {
    if let Err(e) = step.run(dir) {
        println!("⚠️  'prettier' failed or is unavailable ({})", e);
    }
}
