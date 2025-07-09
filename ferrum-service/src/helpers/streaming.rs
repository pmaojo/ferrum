//! Streaming helpers.
//!
//! Abstractions for consuming log output or other text streams.

use std::sync::{Arc, Mutex};

/// Sink for streaming lines of text.
pub trait LogSink: Send + Sync {
    /// Append a line to the sink.
    fn line(&self, text: &str);
}

/// Sink that writes to standard output.
pub struct StdoutSink;

impl LogSink for StdoutSink {
    fn line(&self, text: &str) {
        println!("{}", text);
    }
}

/// In-memory sink used for testing.
#[derive(Default, Clone)]
pub struct MemorySink {
    lines: Arc<Mutex<Vec<String>>>,
}

impl MemorySink {
    /// Return all captured lines.
    pub fn lines(&self) -> Vec<String> {
        self.lines.lock().unwrap().clone()
    }
}

impl LogSink for MemorySink {
    fn line(&self, text: &str) {
        self.lines.lock().unwrap().push(text.to_owned());
    }
}
