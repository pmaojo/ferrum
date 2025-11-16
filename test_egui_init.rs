#!/usr/bin/env rust-script
//! Test script to initialize an EGUI project using ferrum init logic
//!
//! ```cargo
//! [dependencies]
//! ```

use std::fs;
use std::path::PathBuf;

fn main() {
    let name = "todo-app";
    let project_dir = PathBuf::from(name);
    
    println!("🏗️  Initializing new Ferrum EGUI project: {}", name);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    
    // Create project directory
    fs::create_dir_all(&project_dir).unwrap();
    
    // Create workspace Cargo.toml
    fs::write(
        project_dir.join("Cargo.toml"),
        r#"[workspace]
members = [
    "backend",
    "frontend_egui",
    "shared-models",
]

[workspace.package]
version = "0.1.0"
edition = "2021"
"#,
    ).unwrap();
    println!("📄 Created workspace Cargo.toml");
    
    // Create directories
    let dirs = vec![
        "backend/src",
        "shared-models/src",
        "frontend_egui/src",
        "frontend_egui/src/views",
        "frontend_egui/src/forms",
        "frontend_egui/src/api",
        "templates/backend",
        "templates/shared-models",
        "templates/frontend_egui",
        "gen",
    ];
    
    for dir in dirs.iter() {
        fs::create_dir_all(project_dir.join(dir)).unwrap();
        println!("📁 Created directory: {}/{}", name, dir);
    }
    
    // Create backend Cargo.toml
    fs::write(
        project_dir.join("backend/Cargo.toml"),
        r#"[package]
name = "backend"
version = "0.1.0"
edition = "2021"

[dependencies]
axum = "0.7"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1.0"
uuid = { version = "1.0", features = ["serde", "v4"] }
shared-models = { path = "../shared-models" }
"#,
    ).unwrap();
    
    // Create backend main.rs with TODO API
    fs::write(
        project_dir.join("backend/src/main.rs"),
        r#"use axum::{
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

    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
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
"#,
    ).unwrap();
    
    println!("📄 Created backend with TODO API");
    
    // Create shared-models
    fs::write(
        project_dir.join("shared-models/Cargo.toml"),
        r#"[package]
name = "shared-models"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
uuid = { version = "1.0", features = ["serde", "v4"] }
chrono = { version = "0.4", features = ["serde"] }
"#,
    ).unwrap();
    
    fs::write(
        project_dir.join("shared-models/src/lib.rs"),
        r#"use serde::{Deserialize, Serialize};
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Todo {
    pub id: Uuid,
    pub title: String,
    pub description: String,
    pub completed: bool,
}

impl Todo {
    pub fn new(title: String, description: String) -> Self {
        Self {
            id: Uuid::new_v4(),
            title,
            description,
            completed: false,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateTodoRequest {
    pub title: String,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UpdateTodoRequest {
    pub title: Option<String>,
    pub description: Option<String>,
    pub completed: Option<bool>,
}
"#,
    ).unwrap();
    
    println!("📄 Created shared-models crate");
    
    // Create EGUI frontend
    fs::write(
        project_dir.join("frontend_egui/Cargo.toml"),
        r#"[package]
name = "frontend_egui"
version = "0.1.0"
edition = "2021"

[dependencies]
eframe = "0.27"
egui = "0.27"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
reqwest = { version = "0.11", features = ["json", "blocking"] }
tokio = { version = "1", features = ["rt", "rt-multi-thread"] }
anyhow = "1.0"
uuid = { version = "1.0", features = ["serde", "v4"] }
chrono = { version = "0.4", features = ["serde"] }
shared-models = { path = "../shared-models" }
"#,
    ).unwrap();
    
    // Create EGUI main.rs
    fs::write(
        project_dir.join("frontend_egui/src/main.rs"),
        r#"mod app;
mod state;
mod navigation;
mod views;
mod forms;
mod api;

use app::App;

fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1024.0, 768.0]),
        ..Default::default()
    };
    
    eframe::run_native(
        "Ferrum Todo App",
        options,
        Box::new(|cc| Box::new(App::new(cc))),
    )
}
"#,
    ).unwrap();
    
    // Create app.rs with TODO functionality
    fs::write(
        project_dir.join("frontend_egui/src/app.rs"),
        r#"use crate::api::ApiClient;
use crate::navigation::View;
use crate::state::AppState;
use shared_models::{Todo, CreateTodoRequest, UpdateTodoRequest};

pub struct App {
    state: AppState,
    current_view: View,
    api_client: ApiClient,
    
    // Form state
    new_todo_title: String,
    new_todo_description: String,
    error_message: Option<String>,
}

impl App {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        Self {
            state: AppState::new(),
            current_view: View::TodoList,
            api_client: ApiClient::new("http://localhost:3000".to_string()),
            new_todo_title: String::new(),
            new_todo_description: String::new(),
            error_message: None,
        }
    }

    fn render_navigation(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("📝 Ferrum Todo App");
            ui.separator();
            
            for view in View::all() {
                if ui.selectable_label(self.current_view == *view, view.name()).clicked() {
                    self.current_view = *view;
                }
            }
            
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui.button("🔄 Refresh").clicked() {
                    self.load_todos();
                }
            });
        });
        ui.separator();
    }

    fn render_current_view(&mut self, ui: &mut egui::Ui) {
        match self.current_view {
            View::TodoList => self.render_todo_list(ui),
            View::CreateTodo => self.render_create_todo(ui),
        }
    }
    
    fn render_todo_list(&mut self, ui: &mut egui::Ui) {
        ui.heading("Todo List");
        
        if let Some(error) = &self.error_message {
            ui.colored_label(egui::Color32::RED, format!("Error: {}", error));
        }
        
        ui.separator();
        
        egui::ScrollArea::vertical().show(ui, |ui| {
            for todo in &self.state.todos {
                ui.group(|ui| {
                    ui.horizontal(|ui| {
                        let mut completed = todo.completed;
                        if ui.checkbox(&mut completed, "").changed() {
                            self.toggle_todo(todo.id, completed);
                        }
                        
                        ui.vertical(|ui| {
                            if todo.completed {
                                ui.label(egui::RichText::new(&todo.title).strikethrough());
                            } else {
                                ui.label(egui::RichText::new(&todo.title).strong());
                            }
                            ui.label(&todo.description);
                        });
                        
                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if ui.button("🗑").clicked() {
                                self.delete_todo(todo.id);
                            }
                        });
                    });
                });
            }
        });
        
        if self.state.todos.is_empty() {
            ui.vertical_centered(|ui| {
                ui.add_space(50.0);
                ui.label("No todos yet. Create one to get started!");
            });
        }
    }
    
    fn render_create_todo(&mut self, ui: &mut egui::Ui) {
        ui.heading("Create New Todo");
        ui.separator();
        
        if let Some(error) = &self.error_message {
            ui.colored_label(egui::Color32::RED, format!("Error: {}", error));
        }
        
        ui.add_space(10.0);
        
        ui.label("Title:");
        ui.text_edit_singleline(&mut self.new_todo_title);
        
        ui.add_space(10.0);
        
        ui.label("Description:");
        ui.text_edit_multiline(&mut self.new_todo_description);
        
        ui.add_space(20.0);
        
        ui.horizontal(|ui| {
            if ui.button("Create Todo").clicked() {
                self.create_todo();
            }
            
            if ui.button("Cancel").clicked() {
                self.new_todo_title.clear();
                self.new_todo_description.clear();
                self.current_view = View::TodoList;
            }
        });
    }
    
    fn load_todos(&mut self) {
        match self.api_client.get::<Vec<Todo>>("/api/todos") {
            Ok(todos) => {
                self.state.todos = todos;
                self.error_message = None;
            }
            Err(e) => {
                self.error_message = Some(format!("Failed to load todos: {}", e));
            }
        }
    }
    
    fn create_todo(&mut self) {
        if self.new_todo_title.trim().is_empty() {
            self.error_message = Some("Title cannot be empty".to_string());
            return;
        }
        
        let request = CreateTodoRequest {
            title: self.new_todo_title.clone(),
            description: self.new_todo_description.clone(),
        };
        
        match self.api_client.post::<CreateTodoRequest, Todo>("/api/todos", &request) {
            Ok(todo) => {
                self.state.todos.push(todo);
                self.new_todo_title.clear();
                self.new_todo_description.clear();
                self.current_view = View::TodoList;
                self.error_message = None;
            }
            Err(e) => {
                self.error_message = Some(format!("Failed to create todo: {}", e));
            }
        }
    }
    
    fn toggle_todo(&mut self, id: uuid::Uuid, completed: bool) {
        let request = UpdateTodoRequest {
            title: None,
            description: None,
            completed: Some(completed),
        };
        
        match self.api_client.put::<UpdateTodoRequest, Todo>(
            &format!("/api/todos/{}", id),
            &request,
        ) {
            Ok(updated_todo) => {
                if let Some(todo) = self.state.todos.iter_mut().find(|t| t.id == id) {
                    *todo = updated_todo;
                }
                self.error_message = None;
            }
            Err(e) => {
                self.error_message = Some(format!("Failed to update todo: {}", e));
            }
        }
    }
    
    fn delete_todo(&mut self, id: uuid::Uuid) {
        match self.api_client.delete(&format!("/api/todos/{}", id)) {
            Ok(_) => {
                self.state.todos.retain(|t| t.id != id);
                self.error_message = None;
            }
            Err(e) => {
                self.error_message = Some(format!("Failed to delete todo: {}", e));
            }
        }
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Load todos on first frame
        if ctx.frame_nr() == 0 {
            self.load_todos();
        }
        
        egui::CentralPanel::default().show(ctx, |ui| {
            self.render_navigation(ui);
            ui.add_space(10.0);
            self.render_current_view(ui);
        });
    }
}
"#,
    ).unwrap();
    
    // Create state.rs
    fs::write(
        project_dir.join("frontend_egui/src/state.rs"),
        r#"use shared_models::Todo;

#[derive(Default)]
pub struct AppState {
    pub todos: Vec<Todo>,
}

impl AppState {
    pub fn new() -> Self {
        Self::default()
    }
}
"#,
    ).unwrap();
    
    // Create navigation.rs
    fs::write(
        project_dir.join("frontend_egui/src/navigation.rs"),
        r#"#[derive(Debug, Clone, Copy, PartialEq, Eq)]
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
"#,
    ).unwrap();
    
    // Create views/mod.rs
    fs::write(
        project_dir.join("frontend_egui/src/views/mod.rs"),
        "// Generated views will be added here\n",
    ).unwrap();
    
    // Create forms/mod.rs
    fs::write(
        project_dir.join("frontend_egui/src/forms/mod.rs"),
        "// Generated forms will be added here\n",
    ).unwrap();
    
    // Create api/mod.rs
    fs::write(
        project_dir.join("frontend_egui/src/api/mod.rs"),
        r#"mod client;

pub use client::ApiClient;
"#,
    ).unwrap();
    
    // Create api/client.rs
    fs::write(
        project_dir.join("frontend_egui/src/api/client.rs"),
        r#"use anyhow::Result;
use serde::{Deserialize, Serialize};

pub struct ApiClient {
    base_url: String,
    client: reqwest::blocking::Client,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: reqwest::blocking::Client::new(),
        }
    }

    pub fn get<T: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<T> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.get(&url).send()?;
        let data = response.json()?;
        Ok(data)
    }

    pub fn post<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.post(&url).json(body).send()?;
        let data = response.json()?;
        Ok(data)
    }
    
    pub fn put<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        let url = format!("{}{}", self.base_url, path);
        let response = self.client.put(&url).json(body).send()?;
        let data = response.json()?;
        Ok(data)
    }
    
    pub fn delete(&self, path: &str) -> Result<()> {
        let url = format!("{}{}", self.base_url, path);
        self.client.delete(&url).send()?;
        Ok(())
    }
}
"#,
    ).unwrap();
    
    println!("📄 Created EGUI frontend with Todo functionality");
    
    // Create README
    fs::write(
        project_dir.join("README.md"),
        r#"# Ferrum Todo App (EGUI)

A full-stack todo application built with Ferrum framework using EGUI for the native desktop frontend.

## Project Structure

- `backend/`: Rust backend using Axum with REST API
- `frontend_egui/`: EGUI native desktop frontend
- `shared-models/`: Shared data models between backend and frontend

## Getting Started

### Run the Backend

```bash
cargo run -p backend
```

The API will be available at `http://localhost:3000`

### Run the Frontend

In a separate terminal:

```bash
cargo run -p frontend_egui
```

## Features

- ✅ Create todos
- ✅ List all todos
- ✅ Mark todos as complete/incomplete
- ✅ Delete todos
- ✅ Native desktop UI with EGUI
- ✅ REST API backend with Axum
- ✅ Shared type-safe models

## API Endpoints

- `GET /api/todos` - List all todos
- `POST /api/todos` - Create a new todo
- `GET /api/todos/:id` - Get a specific todo
- `PUT /api/todos/:id` - Update a todo
- `DELETE /api/todos/:id` - Delete a todo
"#,
    ).unwrap();
    
    println!("📄 Created README.md");
    
    println!();
    println!("✅ Project initialized successfully!");
    println!("📂 Project location: {}", project_dir.display());
    println!();
    println!("Next steps:");
    println!("  1. cd {}", name);
    println!("  2. cargo run -p backend     # Start the API server");
    println!("  3. cargo run -p frontend_egui  # Start the EGUI app (in another terminal)");
}
