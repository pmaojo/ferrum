use crate::api::ApiClient;
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
            api_client: ApiClient::new("http://localhost:3001".to_string()),
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
