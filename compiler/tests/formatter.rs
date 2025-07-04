use anyhow::Result;
use ferrum_compiler::{format_frontend, format_rust, FormatStep};
use std::path::Path;
use std::sync::{
    atomic::{AtomicUsize, Ordering},
    Arc,
};

struct MockFormatter {
    calls: Arc<AtomicUsize>,
}

impl FormatStep for MockFormatter {
    fn run(&self, _dir: &Path) -> Result<()> {
        self.calls.fetch_add(1, Ordering::SeqCst);
        Ok(())
    }
}

#[test]
fn format_rust_invokes_formatter() {
    let calls = Arc::new(AtomicUsize::new(0));
    let mock = MockFormatter {
        calls: calls.clone(),
    };
    format_rust(&mock, Path::new("."));
    assert_eq!(calls.load(Ordering::SeqCst), 1);
}

#[test]
fn format_frontend_invokes_formatter() {
    let calls = Arc::new(AtomicUsize::new(0));
    let mock = MockFormatter {
        calls: calls.clone(),
    };
    format_frontend(&mock, Path::new("."));
    assert_eq!(calls.load(Ordering::SeqCst), 1);
}

#[test]
fn formatting_error_is_ignored() {
    struct Failing;
    impl FormatStep for Failing {
        fn run(&self, _dir: &Path) -> Result<()> {
            Err(anyhow::anyhow!("fail"))
        }
    }
    format_rust(&Failing, Path::new("."));
    format_frontend(&Failing, Path::new("."));
}
