use ferrum_service::helpers::streaming::{LogSink, MemorySink};

#[test]
fn memory_sink_collects_lines() {
    let sink = MemorySink::default();
    sink.line("a");
    sink.line("b");
    assert_eq!(sink.lines(), vec!["a".to_string(), "b".to_string()]);
}
