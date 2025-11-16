# Ferrum Todo App (EGUI)

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
