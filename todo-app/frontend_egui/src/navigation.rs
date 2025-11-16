#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum View {
    TodoList,
    CreateTodo,
}

impl View {
    pub fn all() -> &'static [View] {
        &[View::TodoList, View::CreateTodo]
    }

    pub fn name(&self) -> &'static str {
        match self {
            View::TodoList => "📋 List",
            View::CreateTodo => "➕ New Todo",
        }
    }
}
