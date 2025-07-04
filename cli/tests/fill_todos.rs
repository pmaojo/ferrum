use ferrum_cli::commands::fill_todos_with_pattern;
use tempfile::tempdir;

#[test]
fn fill_todos_returns_err_on_invalid_regex() {
    let dir = tempdir().unwrap();
    let result = fill_todos_with_pattern(dir.path().to_path_buf(), "(");
    assert!(result.is_err());
}
