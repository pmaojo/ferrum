# EGUI Frontend Support - Design Document

## Overview

This design document outlines the implementation of EGUI (eframe/egui) as a first-class frontend option in Ferrum. EGUI is an immediate mode GUI library for Rust that produces native desktop applications. The implementation will follow Ferrum's existing patterns for code generation while adapting to EGUI's immediate mode paradigm.

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────────┐
│                     Ferrum CLI                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ferrum init  │  │ferrum compile│  │  ferrum dev  │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
└─────────┼──────────────────┼──────────────────┼──────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                  EGUI Generator Module                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  EguiGen (new module in compiler)                    │   │
│  │  - generate_egui_app()                               │   │
│  │  - generate_egui_view()                              │   │
│  │  - generate_egui_form()                              │   │
│  │  - generate_egui_api_client()                        │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Generated EGUI Project Structure                │
│                                                              │
│  frontend_egui/                                             │
│  ├── Cargo.toml                                             │
│  ├── src/                                                   │
│  │   ├── main.rs          (eframe app entry)               │
│  │   ├── app.rs           (main App struct)                │
│  │   ├── views/           (generated views)                │
│  │   │   ├── mod.rs                                        │
│  │   │   ├── user_view.rs                                  │
│  │   │   └── ...                                           │
│  │   ├── forms/           (generated forms)                │
│  │   │   ├── mod.rs                                        │
│  │   │   ├── login_form.rs                                 │
│  │   │   └── ...                                           │
│  │   ├── api/             (API client)                     │
│  │   │   ├── mod.rs                                        │
│  │   │   ├── client.rs                                     │
│  │   │   └── endpoints.rs                                  │
│  │   ├── state.rs         (app state management)           │
│  │   └── navigation.rs    (view routing)                   │
│  └── assets/              (icons, fonts)                    │
│                                                              │
│  backend/                 (unchanged - Axum REST API)       │
│  shared-models/           (shared Rust types)               │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Existing System

The EGUI generator will integrate into Ferrum's existing architecture:

1. **CLI Layer** (`apps/cli/src/commands/`)
   - Add `Egui` variant to `Frontend` enum
   - Update `init.rs` to scaffold EGUI projects
   - Update `dev.rs` to run EGUI apps with cargo-watch

2. **Compiler Layer** (`apps/compiler/src/`)
   - New module: `eguigen.rs` for EGUI-specific generation
   - Extend `generator.rs` to route to EGUI generators when appropriate
   - Add EGUI templates to `templates/frontend_egui/`

3. **Template Layer** (`templates/`)
   - New directory: `templates/frontend_egui/` with Tera templates
   - Templates for: app structure, views, forms, API client, navigation

## Components and Interfaces

### 1. EguiGen Module

New file: `apps/compiler/src/eguigen.rs`

```rust
use anyhow::Result;
use ferrum_shared_models::{Module, Node, NodeType};
use crate::ProjectPaths;

pub struct EguiGenerator {
    paths: ProjectPaths,
}

impl EguiGenerator {
    pub fn new(paths: ProjectPaths) -> Self {
        Self { paths }
    }

    /// Generate the main EGUI application structure
    pub fn generate_app(&self, modules: &[Module]) -> Result<()>;

    /// Generate a view module for an entity
    pub fn generate_view(&self, module: &Module, node: &Node) -> Result<()>;

    /// Generate a form for data input
    pub fn generate_form(&self, module: &Module, node: &Node) -> Result<()>;

    /// Generate API client code
    pub fn generate_api_client(&self, modules: &[Module]) -> Result<()>;

    /// Generate navigation/routing logic
    pub fn generate_navigation(&self, modules: &[Module]) -> Result<()>;

    /// Generate state management
    pub fn generate_state(&self, modules: &[Module]) -> Result<()>;
}
```

### 2. Frontend Enum Extension

File: `apps/cli/src/commands/mod.rs`

```rust
#[derive(Debug, Clone, Copy)]
pub enum Frontend {
    React,
    Egui,
}

impl Frontend {
    pub fn as_str(&self) -> &'static str {
        match self {
            Frontend::React => "react",
            Frontend::Egui => "egui",
        }
    }
}
```

### 3. EGUI App Structure

The generated EGUI app will follow this structure:

```rust
// main.rs
fn main() -> Result<(), eframe::Error> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1280.0, 720.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Ferrum App",
        options,
        Box::new(|cc| Box::new(App::new(cc))),
    )
}

// app.rs
pub struct App {
    state: AppState,
    current_view: View,
    api_client: ApiClient,
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            self.render_navigation(ui);
            self.render_current_view(ui);
        });
    }
}
```

### 4. View Generation Pattern

Each entity will generate a view module:

```rust
// views/user_view.rs
use egui::Ui;
use crate::api::ApiClient;
use crate::state::AppState;

pub struct UserView {
    users: Vec<User>,
    loading: bool,
    error: Option<String>,
}

impl UserView {
    pub fn new() -> Self {
        Self {
            users: Vec::new(),
            loading: false,
            error: None,
        }
    }

    pub fn render(&mut self, ui: &mut Ui, api: &ApiClient, state: &mut AppState) {
        ui.heading("Users");
        
        if self.loading {
            ui.spinner();
        } else if let Some(err) = &self.error {
            ui.colored_label(egui::Color32::RED, err);
        } else {
            self.render_user_list(ui);
        }
        
        if ui.button("Refresh").clicked() {
            self.load_users(api);
        }
    }

    fn render_user_list(&mut self, ui: &mut Ui) {
        egui::ScrollArea::vertical().show(ui, |ui| {
            for user in &self.users {
                ui.horizontal(|ui| {
                    ui.label(&user.name);
                    ui.label(&user.email);
                });
            }
        });
    }

    fn load_users(&mut self, api: &ApiClient) {
        self.loading = true;
        // Async call handled via channels or polling
    }
}
```

### 5. Form Generation Pattern

Forms will be generated with validation:

```rust
// forms/login_form.rs
use egui::Ui;

pub struct LoginForm {
    pub email: String,
    pub password: String,
    pub error: Option<String>,
}

impl LoginForm {
    pub fn new() -> Self {
        Self {
            email: String::new(),
            password: String::new(),
            error: None,
        }
    }

    pub fn render(&mut self, ui: &mut Ui) -> Option<LoginData> {
        ui.heading("Login");
        
        ui.horizontal(|ui| {
            ui.label("Email:");
            ui.text_edit_singleline(&mut self.email);
        });
        
        ui.horizontal(|ui| {
            ui.label("Password:");
            ui.add(egui::TextEdit::singleline(&mut self.password).password(true));
        });
        
        if let Some(err) = &self.error {
            ui.colored_label(egui::Color32::RED, err);
        }
        
        if ui.button("Login").clicked() {
            if self.validate() {
                return Some(LoginData {
                    email: self.email.clone(),
                    password: self.password.clone(),
                });
            }
        }
        
        None
    }

    fn validate(&mut self) -> bool {
        if self.email.is_empty() {
            self.error = Some("Email is required".to_string());
            return false;
        }
        if !self.email.contains('@') {
            self.error = Some("Invalid email format".to_string());
            return false;
        }
        self.error = None;
        true
    }
}
```

### 6. API Client

The API client will use reqwest with tokio:

```rust
// api/client.rs
use anyhow::Result;
use serde::{Deserialize, Serialize};

pub struct ApiClient {
    base_url: String,
    client: reqwest::Client,
    runtime: tokio::runtime::Runtime,
}

impl ApiClient {
    pub fn new(base_url: String) -> Self {
        Self {
            base_url,
            client: reqwest::Client::new(),
            runtime: tokio::runtime::Runtime::new().unwrap(),
        }
    }

    pub fn get<T: for<'de> Deserialize<'de>>(&self, path: &str) -> Result<T> {
        self.runtime.block_on(async {
            let url = format!("{}{}", self.base_url, path);
            let response = self.client.get(&url).send().await?;
            let data = response.json().await?;
            Ok(data)
        })
    }

    pub fn post<T: Serialize, R: for<'de> Deserialize<'de>>(
        &self,
        path: &str,
        body: &T,
    ) -> Result<R> {
        self.runtime.block_on(async {
            let url = format!("{}{}", self.base_url, path);
            let response = self.client.post(&url).json(body).send().await?;
            let data = response.json().await?;
            Ok(data)
        })
    }
}
```

### 7. Navigation System

```rust
// navigation.rs
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum View {
    Home,
    Users,
    Login,
    // Generated from routes in YAML
}

impl View {
    pub fn all() -> &'static [View] {
        &[View::Home, View::Users, View::Login]
    }

    pub fn name(&self) -> &'static str {
        match self {
            View::Home => "Home",
            View::Users => "Users",
            View::Login => "Login",
        }
    }

    pub fn requires_auth(&self) -> bool {
        match self {
            View::Login => false,
            _ => true,
        }
    }
}
```

## Data Models

### AppState

```rust
pub struct AppState {
    pub user: Option<User>,
    pub token: Option<String>,
    pub theme: Theme,
}

impl AppState {
    pub fn is_authenticated(&self) -> bool {
        self.token.is_some()
    }

    pub fn logout(&mut self) {
        self.user = None;
        self.token = None;
    }
}
```

### Shared Models

EGUI will use the same shared-models as the backend, ensuring type safety:

```rust
// shared-models/user.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: uuid::Uuid,
    pub name: String,
    pub email: String,
    pub created_at: chrono::NaiveDateTime,
}
```

## Error Handling

### Error Display Strategy

1. **Network Errors**: Display in UI with retry button
2. **Validation Errors**: Show inline with form fields
3. **Authentication Errors**: Redirect to login view
4. **Server Errors**: Show error dialog with details

```rust
pub enum AppError {
    Network(String),
    Validation(String),
    Auth(String),
    Server(String),
}

impl AppError {
    pub fn display(&self, ui: &mut Ui) {
        let (color, message) = match self {
            AppError::Network(msg) => (egui::Color32::YELLOW, format!("Network: {}", msg)),
            AppError::Validation(msg) => (egui::Color32::ORANGE, format!("Validation: {}", msg)),
            AppError::Auth(msg) => (egui::Color32::RED, format!("Auth: {}", msg)),
            AppError::Server(msg) => (egui::Color32::RED, format!("Server: {}", msg)),
        };
        ui.colored_label(color, message);
    }
}
```

## Testing Strategy

### Unit Tests

1. **Form Validation**: Test validation logic independently
2. **API Client**: Mock HTTP responses
3. **State Management**: Test state transitions
4. **Navigation**: Test view routing logic

### Integration Tests

1. **Full App Flow**: Test complete user workflows
2. **API Integration**: Test against real backend
3. **Error Scenarios**: Test error handling paths

### Example Test

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn login_form_validates_email() {
        let mut form = LoginForm::new();
        form.email = "invalid".to_string();
        form.password = "password123".to_string();
        
        assert!(!form.validate());
        assert!(form.error.is_some());
    }

    #[test]
    fn login_form_accepts_valid_input() {
        let mut form = LoginForm::new();
        form.email = "user@example.com".to_string();
        form.password = "password123".to_string();
        
        assert!(form.validate());
        assert!(form.error.is_none());
    }
}
```

## Template Structure

### Directory Layout

```
templates/frontend_egui/
├── main.rs.tera
├── app.rs.tera
├── state.rs.tera
├── navigation.rs.tera
├── Cargo.toml.tera
├── views/
│   ├── mod.rs.tera
│   └── view.rs.tera
├── forms/
│   ├── mod.rs.tera
│   └── form.rs.tera
└── api/
    ├── mod.rs.tera
    ├── client.rs.tera
    └── endpoints.rs.tera
```

### Template Context

Templates will receive context similar to existing generators:

```rust
#[derive(Serialize)]
struct EguiViewContext<'a> {
    module_name: &'a str,
    entity_name: &'a str,
    fields: Vec<EguiField>,
    has_auth: bool,
}

#[derive(Serialize)]
struct EguiField {
    name: String,
    rust_type: String,
    widget_type: String, // "text_edit", "drag_value", "checkbox", etc.
    validation: Option<String>,
}
```

## Development Workflow

### ferrum init

```bash
ferrum init my-app --frontend egui
```

Creates:
- `frontend_egui/` directory with EGUI app structure
- `backend/` with Axum API
- `shared-models/` for shared types
- `Cargo.toml` workspace configuration

### ferrum compile

```bash
ferrum compile gen/users.yaml
```

Generates:
- EGUI views for entities
- EGUI forms for usecases
- API client endpoints
- Navigation routes

### ferrum dev

```bash
ferrum dev
```

Runs:
- Backend with cargo watch
- EGUI app with cargo watch
- Both reload on file changes

## Dependencies

### EGUI Frontend Cargo.toml

```toml
[package]
name = "frontend_egui"
version = "0.1.0"
edition = "2024"

[dependencies]
eframe = "0.27"
egui = "0.27"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
reqwest = { version = "0.11", features = ["json", "blocking"] }
tokio = { version = "1", features = ["rt", "rt-multi-thread"] }
anyhow = "1.0"
uuid = { version = "1.0", features = ["serde"] }
chrono = { version = "0.4", features = ["serde"] }

# Shared models from workspace
shared-models = { path = "../shared-models" }
```

## Migration Path

### From React to EGUI

Users can regenerate their project with EGUI:

```bash
# Backup existing frontend
mv frontend frontend_react_backup

# Regenerate with EGUI
ferrum compile gen/*.yaml --frontend egui
```

The backend and shared-models remain unchanged, ensuring a smooth transition.

## Performance Considerations

1. **Async Operations**: Use channels or polling for non-blocking API calls
2. **Rendering**: EGUI's immediate mode is efficient for most UIs
3. **Large Lists**: Use `egui::ScrollArea` with virtual scrolling for large datasets
4. **State Updates**: Minimize state clones, use `Arc` where appropriate

## Security Considerations

1. **Token Storage**: Store JWT tokens securely in memory only
2. **HTTPS**: Enforce HTTPS for API calls in production
3. **Input Validation**: Validate all user input before sending to API
4. **Error Messages**: Don't expose sensitive information in error messages
