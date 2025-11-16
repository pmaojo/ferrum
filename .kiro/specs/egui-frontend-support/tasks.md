# Implementation Plan

- [x] 1. Set up EGUI infrastructure and CLI integration
  - Add `Egui` variant to `Frontend` enum in `apps/cli/src/commands/mod.rs`
  - Update `init.rs` to handle `--frontend egui` flag
  - Create `frontend_egui/` directory structure during init
  - Generate initial `Cargo.toml` for EGUI workspace
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Create EGUI generator module
  - [x] 2.1 Create `apps/compiler/src/eguigen.rs` with `EguiGenerator` struct
    - Implement `new()` constructor taking `ProjectPaths`
    - Add module declaration in `apps/compiler/src/lib.rs`
    - _Requirements: 2.1, 2.2, 6.1_

  - [x] 2.2 Implement main app generation
    - Create `generate_app()` method to scaffold EGUI app structure
    - Generate `main.rs` with eframe entry point
    - Generate `app.rs` with main `App` struct and `eframe::App` trait implementation
    - _Requirements: 1.5, 6.2_

  - [x] 2.3 Implement state management generation
    - Create `generate_state()` method
    - Generate `state.rs` with `AppState` struct
    - Include authentication state (user, token)
    - _Requirements: 6.3, 7.4_

  - [x] 2.4 Implement navigation generation
    - Create `generate_navigation()` method
    - Generate `navigation.rs` with `View` enum from routes
    - Implement view switching logic
    - Add `requires_auth()` checks for protected routes
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 3. Implement view generation from entities
  - [x] 3.1 Create view generation method
    - Implement `generate_view()` method in `EguiGenerator`
    - Generate view modules in `frontend_egui/src/views/`
    - Create `mod.rs` to export all views
    - _Requirements: 2.1, 2.6_

  - [x] 3.2 Generate entity display widgets
    - Map entity fields to EGUI widgets (TextEdit, DragValue, Checkbox)
    - Generate `render()` method for each view
    - Add loading and error states
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [x] 3.3 Add list and detail views
    - Generate ScrollArea for entity lists
    - Create detail view for individual entities
    - Add navigation between list and detail
    - _Requirements: 2.1, 2.6_

- [ ] 4. Implement form generation
  - [ ] 4.1 Create form generation method
    - Implement `generate_form()` method in `EguiGenerator`
    - Generate form modules in `frontend_egui/src/forms/`
    - Create `mod.rs` to export all forms
    - _Requirements: 2.1, 2.6_

  - [ ] 4.2 Generate form widgets with validation
    - Map form fields to appropriate EGUI input widgets
    - Generate inline validation logic
    - Add error display for validation failures
    - Generate submit button with validation check
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [ ] 4.3 Integrate forms with API client
    - Generate form submission logic calling API endpoints
    - Handle success and error responses
    - Update app state after successful submission
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 5. Implement API client generation
  - [ ] 5.1 Create API client structure
    - Implement `generate_api_client()` method
    - Generate `api/client.rs` with `ApiClient` struct
    - Initialize reqwest client and tokio runtime
    - _Requirements: 3.1, 3.4_

  - [ ] 5.2 Generate endpoint methods
    - Create GET, POST, PUT, DELETE methods for each usecase
    - Use shared-models types for request/response
    - Implement error handling with `Result` types
    - _Requirements: 3.2, 3.3, 3.4, 3.5_

  - [ ] 5.3 Add authentication support
    - Include JWT token in request headers when available
    - Handle 401 responses by clearing auth state
    - _Requirements: 3.5, 7.4_

- [ ] 6. Create EGUI templates
  - [ ] 6.1 Create template directory structure
    - Create `templates/frontend_egui/` directory
    - Add subdirectories: `views/`, `forms/`, `api/`
    - _Requirements: 6.1, 6.2_

  - [ ] 6.2 Create core app templates
    - Create `main.rs.tera` template
    - Create `app.rs.tera` template with eframe::App implementation
    - Create `state.rs.tera` template
    - Create `navigation.rs.tera` template
    - Create `Cargo.toml.tera` template with dependencies
    - _Requirements: 1.5, 1.6, 6.3, 6.4, 6.5_

  - [ ] 6.3 Create view templates
    - Create `views/mod.rs.tera` template
    - Create `views/view.rs.tera` template for entity views
    - Include widget generation logic based on field types
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 6.4 Create form templates
    - Create `forms/mod.rs.tera` template
    - Create `forms/form.rs.tera` template
    - Include validation logic generation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 6.5 Create API client templates
    - Create `api/mod.rs.tera` template
    - Create `api/client.rs.tera` template
    - Create `api/endpoints.rs.tera` template for generated endpoints
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 7. Integrate EGUI generator into compiler pipeline
  - Update `generator.rs` to detect EGUI frontend option
  - Route entity nodes to `EguiGenerator::generate_view()`
  - Route form nodes to `EguiGenerator::generate_form()`
  - Call `generate_api_client()` after processing all modules
  - Call `generate_navigation()` to create routing
  - _Requirements: 2.1, 2.2, 3.1, 7.1_

- [ ] 8. Update ferrum dev command for EGUI
  - Modify `apps/cli/src/commands/dev.rs` to detect EGUI frontend
  - Start EGUI app with `cargo watch -x run -p frontend_egui`
  - Run backend and EGUI in parallel
  - Display combined logs in terminal
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 9. Update ferrum build command for EGUI
  - Modify `apps/cli/src/commands/build.rs` to handle EGUI
  - Build EGUI frontend with `cargo build --release -p frontend_egui`
  - Support `--target` flag for cross-compilation
  - Output binary location to user
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [ ] 10. Add interactive mode support for EGUI
  - Update interactive prompt in `init.rs` to include EGUI option
  - Present "EGUI (native desktop)" and "React (web)" as choices
  - Set default based on user selection
  - _Requirements: 1.3_

- [ ] 11. Update documentation
  - Add EGUI section to README.md
  - Document `--frontend egui` flag usage
  - Add examples of generated EGUI code
  - Document development workflow with EGUI
  - Create `docs/egui.md` with detailed guide
  - _Requirements: 1.1, 1.2, 1.3, 4.1, 5.1_

- [ ] 12. Add example EGUI project
  - Create `examples/egui-demo/` directory
  - Include sample `grafo.yaml` with entities, forms, routes
  - Generate complete EGUI app from YAML
  - Add README with build and run instructions
  - _Requirements: 1.1, 2.1, 3.1, 7.1_

- [ ] 13. Add error handling and validation
  - [ ]* 13.1 Implement error display components
    - Create reusable error display widget
    - Add error state to views and forms
    - Show network errors with retry button
    - _Requirements: 3.3_

  - [ ]* 13.2 Add comprehensive validation
    - Generate validation functions from YAML rules
    - Display validation errors inline with form fields
    - Prevent submission when validation fails
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [ ] 14. Add testing infrastructure
  - [ ]* 14.1 Create unit test templates
    - Add test modules to generated views
    - Add test modules to generated forms
    - Test validation logic independently
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 14.2 Add integration test examples
    - Create example integration tests in demo project
    - Test full user workflows
    - Mock API responses for testing
    - _Requirements: 6.4, 6.5_

- [ ] 15. Performance optimizations
  - [ ]* 15.1 Implement async API calls
    - Use channels for non-blocking API communication
    - Add loading spinners during async operations
    - Handle concurrent requests properly
    - _Requirements: 3.2, 4.1_

  - [ ]* 15.2 Optimize rendering
    - Use virtual scrolling for large lists
    - Minimize state clones with Arc where appropriate
    - Profile and optimize hot paths
    - _Requirements: 2.1, 2.6_
