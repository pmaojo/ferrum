use shared_models::Todo;

#[derive(Default)]
pub struct AppState {
    pub todos: Vec<Todo>,
}

impl AppState {
    pub fn new() -> Self {
        Self::default()
    }
}
