use axum::{
    extract::{Path, State},
    http::StatusCode,
    routing::{get, post, put, delete},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::{Arc, Mutex};
use uuid::Uuid;

use shared_models::{Todo, CreateTodoRequest, UpdateTodoRequest};

type TodoStore = Arc<Mutex<HashMap<Uuid, Todo>>>;

#[tokio::main]
async fn main() {
    let store: TodoStore = Arc::new(Mutex::new(HashMap::new()));
    
    let app = Router::new()
        .route("/", get(|| async { "Ferrum Todo API" }))
        .route("/api/todos", get(list_todos))
        .route("/api/todos", post(create_todo))
        .route("/api/todos/:id", get(get_todo))
        .route("/api/todos/:id", put(update_todo))
        .route("/api/todos/:id", delete(delete_todo))
        .with_state(store);

    let addr = SocketAddr::from(([0, 0, 0, 0], 3001));
    println!("🚀 Backend running on {}", addr);
    
    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn list_todos(State(store): State<TodoStore>) -> Json<Vec<Todo>> {
    let todos = store.lock().unwrap();
    Json(todos.values().cloned().collect())
}

async fn create_todo(
    State(store): State<TodoStore>,
    Json(req): Json<CreateTodoRequest>,
) -> (StatusCode, Json<Todo>) {
    let todo = Todo::new(req.title, req.description);
    store.lock().unwrap().insert(todo.id, todo.clone());
    (StatusCode::CREATED, Json(todo))
}

async fn get_todo(
    State(store): State<TodoStore>,
    Path(id): Path<Uuid>,
) -> Result<Json<Todo>, StatusCode> {
    store
        .lock()
        .unwrap()
        .get(&id)
        .cloned()
        .map(Json)
        .ok_or(StatusCode::NOT_FOUND)
}

async fn update_todo(
    State(store): State<TodoStore>,
    Path(id): Path<Uuid>,
    Json(req): Json<UpdateTodoRequest>,
) -> Result<Json<Todo>, StatusCode> {
    let mut todos = store.lock().unwrap();
    let todo = todos.get_mut(&id).ok_or(StatusCode::NOT_FOUND)?;
    
    if let Some(title) = req.title {
        todo.title = title;
    }
    if let Some(description) = req.description {
        todo.description = description;
    }
    if let Some(completed) = req.completed {
        todo.completed = completed;
    }
    
    Ok(Json(todo.clone()))
}

async fn delete_todo(
    State(store): State<TodoStore>,
    Path(id): Path<Uuid>,
) -> StatusCode {
    if store.lock().unwrap().remove(&id).is_some() {
        StatusCode::NO_CONTENT
    } else {
        StatusCode::NOT_FOUND
    }
}
