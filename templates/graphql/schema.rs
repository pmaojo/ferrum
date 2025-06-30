use async_graphql::{EmptyMutation, EmptySubscription, Schema};
use ferrum_engine::services::graphql::QueryRoot;

/// Default GraphQL schema used by Ferrum projects.
pub fn build_schema() -> Schema<QueryRoot, EmptyMutation, EmptySubscription> {
    Schema::build(QueryRoot, EmptyMutation, EmptySubscription).finish()
}
