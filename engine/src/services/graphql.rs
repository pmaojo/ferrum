use async_graphql::{EmptyMutation, EmptySubscription, Object, Schema};

/// Basic query root provided out of the box.
pub struct QueryRoot;

#[Object]
impl QueryRoot {
    /// Simple hello world field to verify the server works.
    async fn hello(&self) -> &str {
        "Hello from Ferrum"
    }
}

/// Create the default GraphQL schema used by Ferrum projects.
pub fn create_schema() -> Schema<QueryRoot, EmptyMutation, EmptySubscription> {
    Schema::build(QueryRoot, EmptyMutation, EmptySubscription).finish()
}
