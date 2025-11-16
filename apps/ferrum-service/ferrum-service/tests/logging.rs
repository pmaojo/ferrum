use ferrum_service::helpers::logging::init;
use tracing::{info, Level};

#[test]
fn init_does_not_panic_on_multiple_calls() {
    init(Level::INFO);
    info!("first");
    init(Level::INFO);
    info!("second");
}
