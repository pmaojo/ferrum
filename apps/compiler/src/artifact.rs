//! Idempotent file reconciliation for generated artifacts.
//!
//! Several generators write into files that are shared by more than one node:
//! `backend/ports.rs`, `backend/src/db/models.rs`, `backend/src/db/schema.rs`
//! and `backend/src/validations/mod.rs`. They used to append, which meant a
//! second `ferrum compile` duplicated every entry — duplicate Rust structs and
//! duplicate `pub mod` lines that do not compile.
//!
//! Instead every generated block is wrapped in a marker pair:
//!
//! ```text
//! // <ferrum:begin entity:user>
//! ...
//! // <ferrum:end entity:user>
//! ```
//!
//! Rewriting a key replaces its block in place, so repeated compiles converge
//! on identical output, and anything the user writes outside the markers is
//! preserved. Duplicate blocks left behind by older versions are collapsed.

use anyhow::{Context, Result};
use std::fs;
use std::path::{Path, PathBuf};

fn begin_marker(key: &str) -> String {
    format!("// <ferrum:begin {key}>")
}

fn end_marker(key: &str) -> String {
    format!("// <ferrum:end {key}>")
}

fn normalize_body(body: &str) -> String {
    body.trim_end_matches(['\n', '\r']).to_string()
}

/// The marker-delimited block for `key` as individual lines.
fn block(key: &str, body: &str) -> Vec<String> {
    let mut lines = vec![begin_marker(key)];
    lines.extend(normalize_body(body).lines().map(str::to_string));
    lines.push(end_marker(key));
    lines
}

/// Inclusive line ranges of every region carrying `key`.
///
/// A `begin` without a matching `end` is ignored: without the closing marker we
/// cannot know where the generated text stops, so it is left as user content.
fn find_regions(lines: &[String], key: &str) -> Vec<(usize, usize)> {
    let begin = begin_marker(key);
    let end = end_marker(key);
    let mut found = Vec::new();
    let mut start: Option<usize> = None;
    for (index, line) in lines.iter().enumerate() {
        let trimmed = line.trim_end();
        match start {
            None if trimmed == begin => start = Some(index),
            Some(from) if trimmed == end => {
                found.push((from, index));
                start = None;
            }
            _ => {}
        }
    }
    found
}

/// Replace the managed region `key` in `path`, inserting it when absent.
///
/// `merge` receives the region's current body (`None` when the region is new)
/// and returns the replacement body, which allows accumulative regions such as
/// module lists.
pub fn upsert_region_with<F>(path: &Path, key: &str, merge: F) -> Result<()>
where
    F: FnOnce(Option<&str>) -> String,
{
    let current = fs::read_to_string(path).unwrap_or_default();
    let mut lines: Vec<String> = current.lines().map(str::to_string).collect();
    let regions = find_regions(&lines, key);

    let existing_body = regions
        .first()
        .map(|(from, to)| lines[from + 1..*to].join("\n"));
    let new_block = block(key, &merge(existing_body.as_deref()));

    match regions.first() {
        Some(&(first_from, first_to)) => {
            // Drop stale duplicates from the end first so the surviving
            // indices stay valid, then replace the first occurrence in place.
            for &(from, to) in regions.iter().skip(1).rev() {
                lines.drain(from..=to);
            }
            lines.splice(first_from..=first_to, new_block);
        }
        None => {
            if lines.iter().any(|line| !line.trim().is_empty()) {
                lines.push(String::new());
            }
            lines.extend(new_block);
        }
    }

    let mut output = lines.join("\n");
    output.push('\n');
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create {}", parent.display()))?;
    }
    fs::write(path, output).with_context(|| format!("failed to write {}", path.display()))?;
    Ok(())
}

/// Replace the managed region `key` with `body`.
pub fn upsert_region(path: &Path, key: &str, body: &str) -> Result<()> {
    let body = normalize_body(body);
    upsert_region_with(path, key, move |_| body)
}

/// Add `line` to an accumulative, de-duplicated, sorted region.
///
/// Used for `pub mod` lists, where each node contributes one line and later
/// compiles must not add it twice.
pub fn add_region_line(path: &Path, key: &str, line: &str) -> Result<()> {
    let wanted = line.trim().to_string();
    upsert_region_with(path, key, move |existing| {
        let mut items: Vec<String> = existing
            .unwrap_or_default()
            .lines()
            .map(|item| item.trim().to_string())
            .filter(|item| !item.is_empty())
            .collect();
        if !items.iter().any(|item| item == &wanted) {
            items.push(wanted.clone());
        }
        items.sort();
        items.dedup();
        items.join("\n")
    })
}

/// Write a migration pair into a directory named after `slug`.
///
/// The directory is derived from `slug` rather than from the current directory
/// count, so recompiling reuses `0001_create_users` instead of creating
/// `0003_create_users` next to it. Existing migrations keep their numbers.
pub fn ensure_migration(root: &Path, slug: &str, up_sql: &str, down_sql: &str) -> Result<()> {
    fs::create_dir_all(root)
        .with_context(|| format!("failed to create {}", root.display()))?;

    let suffix = format!("_{slug}");
    let mut existing: Option<PathBuf> = None;
    let mut highest = 0u32;

    for entry in fs::read_dir(root)? {
        let entry = entry?;
        if !entry.file_type()?.is_dir() {
            continue;
        }
        let name = entry.file_name().to_string_lossy().to_string();
        if let Some((prefix, _)) = name.split_once('_') {
            if let Ok(index) = prefix.parse::<u32>() {
                highest = highest.max(index);
            }
        }
        if name.ends_with(&suffix) {
            existing = Some(entry.path());
        }
    }

    let dir = match existing {
        Some(dir) => dir,
        None => {
            let dir = root.join(format!("{:04}{}", highest + 1, suffix));
            fs::create_dir_all(&dir)
                .with_context(|| format!("failed to create {}", dir.display()))?;
            dir
        }
    };

    fs::write(dir.join("up.sql"), up_sql)?;
    fs::write(dir.join("down.sql"), down_sql)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    fn read(path: &Path) -> String {
        fs::read_to_string(path).unwrap()
    }

    #[test]
    fn upsert_is_idempotent() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("ports.rs");

        upsert_region(&file, "port:userReader", "pub trait UserReader {}").unwrap();
        let first = read(&file);
        upsert_region(&file, "port:userReader", "pub trait UserReader {}").unwrap();
        let second = read(&file);

        assert_eq!(first, second);
        assert_eq!(second.matches("begin port:userReader").count(), 1);
        assert_eq!(second.matches("pub trait UserReader {}").count(), 1);
    }

    #[test]
    fn upsert_keeps_distinct_regions_and_user_code() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("ports.rs");
        fs::write(&file, "// hand written\n").unwrap();

        upsert_region(&file, "port:a", "pub trait A {}").unwrap();
        upsert_region(&file, "port:b", "pub trait B {}").unwrap();
        let _ = &file;
        let content = read(&file);

        assert!(content.contains("// hand written"));
        assert!(content.contains("pub trait A {}"));
        assert!(content.contains("pub trait B {}"));
        assert_eq!(content.matches("pub trait A {}").count(), 1);
        assert_eq!(content.matches("begin port:a").count(), 1);
        assert_eq!(content.matches("begin port:b").count(), 1);
    }

    #[test]
    fn upsert_updates_body_in_place() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("ports.rs");
        upsert_region(&file, "port:a", "pub trait A {}").unwrap();
        upsert_region(&file, "port:a", "pub trait A { fn x(); }").unwrap();
        let content = read(&file);
        assert!(content.contains("fn x()"));
        assert_eq!(content.matches("begin port:a").count(), 1);
    }

    /// A file produced by the old append-based generator contains the same
    /// block twice. Recompiling must heal it down to one.
    #[test]
    fn upsert_collapses_duplicate_regions() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("models.rs");
        let block = "// <ferrum:begin entity:user>\npub struct User;\n// <ferrum:end entity:user>";
        fs::write(&file, format!("{block}\n{block}\n")).unwrap();

        upsert_region(&file, "entity:user", "pub struct User;").unwrap();
        let content = read(&file);

        assert_eq!(content.matches("begin entity:user").count(), 1);
        assert_eq!(content.matches("pub struct User;").count(), 1);
    }

    #[test]
    fn add_region_line_deduplicates_and_sorts() {
        let dir = tempdir().unwrap();
        let file = dir.path().join("mod.rs");
        add_region_line(&file, "modules", "pub mod zebra;").unwrap();
        add_region_line(&file, "modules", "pub mod alpha;").unwrap();
        add_region_line(&file, "modules", "pub mod zebra;").unwrap();
        let content = read(&file);

        assert_eq!(content.matches("pub mod zebra;").count(), 1);
        assert_eq!(content.matches("pub mod alpha;").count(), 1);
        let alpha = content.find("pub mod alpha;").unwrap();
        let zebra = content.find("pub mod zebra;").unwrap();
        assert!(alpha < zebra, "region lines should be sorted");
    }

    #[test]
    fn ensure_migration_reuses_existing_directory() {
        let dir = tempdir().unwrap();
        let root = dir.path().join("migrations");

        ensure_migration(&root, "create_users", "CREATE TABLE users;", "DROP TABLE users;")
            .unwrap();
        ensure_migration(&root, "create_users", "CREATE TABLE users;", "DROP TABLE users;")
            .unwrap();

        let mut names: Vec<String> = fs::read_dir(&root)
            .unwrap()
            .map(|entry| entry.unwrap().file_name().to_string_lossy().to_string())
            .collect();
        names.sort();

        assert_eq!(names, vec!["0001_create_users".to_string()]);
    }

    #[test]
    fn ensure_migration_numbers_distinct_slugs_in_order() {
        let dir = tempdir().unwrap();
        let root = dir.path().join("migrations");

        ensure_migration(&root, "create_users", "up", "down").unwrap();
        ensure_migration(&root, "create_posts", "up", "down").unwrap();
        ensure_migration(&root, "create_users", "up", "down").unwrap();

        let mut names: Vec<String> = fs::read_dir(&root)
            .unwrap()
            .map(|entry| entry.unwrap().file_name().to_string_lossy().to_string())
            .collect();
        names.sort();

        assert_eq!(
            names,
            vec!["0001_create_users".to_string(), "0002_create_posts".to_string()]
        );
    }
}
