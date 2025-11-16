# Ferrum MCP Tools Documentation

This document describes the Model Context Protocol (MCP) tools available for the Ferrum framework integration.

## Overview

The Ferrum MCP server provides a set of tools that allow IDE integrations (like Kiro) to interact with Ferrum projects through a standardized interface. These tools enable:

- Project initialization with various feature flags
- DSL compilation with automatic PermaGraph sync
- AI-powered DSL generation using GraphRAG
- Development environment management
- Project health diagnostics

## Available Tools

### 1. ferrum_init

Initialize a new Ferrum project with specified features and configuration.

**Parameters:**
- `name` (string, required): Project name (must match pattern `^[a-zA-Z][a-zA-Z0-9_-]*$`)
- `with_graph` (boolean, default: false): Include graph database support (Neo4j)
- `with_ai` (boolean, default: false): Include AI/LLM integration features
- `with_db` (boolean, default: false): Include Diesel ORM setup for PostgreSQL
- `with_auth` (boolean, default: false): Include authentication templates
- `with_jobs` (boolean, default: false): Include background job templates
- `with_uploads` (boolean, default: false): Include file upload templates
- `frontend` (string, default: "react"): Frontend framework choice (react, leptos-csr, leptos-ssr)
- `api_only` (boolean, default: false): Backend only project (no frontend)
- `interactive` (boolean, default: false): Use interactive mode for configuration

**Example:**
```json
{
  "name": "my-ferrum-app",
  "with_graph": true,
  "with_ai": true,
  "frontend": "react"
}
```

**Returns:**
- Project creation status
- Enabled features summary
- Next steps for development

### 2. ferrum_compile

Compile Ferrum DSL files to generate code with automatic PermaGraph sync.

**Parameters:**
- `files` (array, required): DSL files to compile (supports glob patterns)
- `output_dir` (string, default: "."): Output directory for generated code
- `templates_dir` (string, default: "templates"): Templates directory path
- `module` (string, optional): Specific module to compile
- `graph_mode` (boolean, default: false): Enable graph mode compilation
- `threads` (integer, 1-16, optional): Number of threads for parallel compilation
- `dry_run` (boolean, default: false): Perform dry run without writing files

**Example:**
```json
{
  "files": ["gen/users.yaml"],
  "output_dir": ".",
  "graph_mode": false
}
```

**Returns:**
- Compilation status
- List of generated files
- PermaGraph sync status

### 3. ferrum_prompt

Generate Ferrum DSL from natural language using AI with GraphRAG context.

**Parameters:**
- `prompt` (string, required, min 10 chars): Natural language description of the desired architecture
- `output_file` (string, default: "grafo.yaml"): Output file for generated DSL
- `context_project` (string, optional): Path to existing project for context
- `use_patterns` (boolean, default: true): Use GraphRAG patterns for enhanced generation
- `ai_model` (string, default: "gpt-4"): AI model to use (gpt-4, gpt-3.5-turbo, claude-3, local-llm)

**Example:**
```json
{
  "prompt": "Create a user management system with authentication and profile management",
  "use_patterns": true,
  "output_file": "gen/user_system.yaml"
}
```

**Returns:**
- Generated DSL file path
- AI model used
- Context information
- DSL preview

### 4. ferrum_doctor

Diagnose Ferrum project health and dependencies.

**Parameters:**
- `project_path` (string, default: "."): Path to Ferrum project to diagnose
- `check_dependencies` (boolean, default: true): Check system dependencies (Rust, Node.js, etc.)
- `check_services` (boolean, default: true): Check external services (database, AI, etc.)
- `verbose` (boolean, default: false): Verbose output with detailed diagnostics

**Example:**
```json
{
  "project_path": ".",
  "check_dependencies": true,
  "check_services": true
}
```

**Returns:**
- Health status (healthy, warning, error)
- Dependency check results
- Service availability
- Recommendations for fixes

### 5. ferrum_dev

Start Ferrum development environment with hot reloading.

**Parameters:**
- `project_path` (string, default: "."): Path to Ferrum project
- `port` (integer, 1024-65535, default: 3000): Backend port
- `frontend_port` (integer, 1024-65535, default: 5173): Frontend port
- `with_graph` (boolean, default: false): Start with graph database
- `with_ai` (boolean, default: false): Start with AI services
- `detached` (boolean, default: false): Run in detached mode

**Example:**
```json
{
  "project_path": ".",
  "with_graph": true,
  "with_ai": true
}
```

**Returns:**
- Development server status
- Service URLs
- Enabled services

## API Endpoints

### GET /tools
Returns list of all available tools with their schemas.

### GET /tools/:toolName
Returns detailed information about a specific tool including examples.

### POST /validate/:toolName
Validates parameters for a tool without executing it.

**Request Body:**
```json
{
  "parameters": {
    // tool parameters
  }
}
```

### POST /execute/:toolName
Executes a tool with the provided parameters.

**Request Body:**
```json
{
  "parameters": {
    // tool parameters
  }
}
```

## Error Handling

The MCP server provides comprehensive error handling:

- **Parameter Validation**: All parameters are validated against JSON schemas
- **Container Availability**: Checks if Ferrum container is running before execution
- **Timeout Handling**: Commands have reasonable timeouts to prevent hanging
- **Graceful Degradation**: Provides helpful error messages and suggestions

## Integration with Visual Development

### SCG Integration
When tools are executed, results can be automatically reflected in the Semantic Code Graph UI:

- Project initialization creates SCG-compatible project structure
- DSL compilation triggers SCG updates
- AI generation results appear in visual editor

### PermaGraph Sync
Compilation tools automatically sync architectural data to PermaGraph for:

- Version history tracking
- Cross-project pattern analysis
- GraphRAG context enhancement

## Testing

Use the provided test script to validate tool definitions and parameter validation:

```bash
# Test parameter validation only
node test-ferrum-tools.js

# Test parameter validation and execution (requires Ferrum container)
node test-ferrum-tools.js --execution
```

## Container Requirements

Most tools require the Ferrum Docker container to be running:

```bash
# Start Ferrum development environment
docker-compose -f docker-compose.ferrum.yml up -d

# Check container status
docker ps --filter name=ferrum-cli
```

## Configuration

Environment variables:
- `MCP_PORT`: Server port (default: 8001)
- `FERRUM_CONTAINER_NAME`: Ferrum container name (default: ferrum-cli)
- `FERRUM_WORKSPACE`: Workspace path in container (default: /workspace)

## Security Considerations

- All parameters are validated against strict schemas
- Command injection is prevented through parameter validation
- Container execution is isolated from host system
- Timeouts prevent resource exhaustion

## Troubleshooting

### Common Issues

1. **Container Not Available**
   - Error: "Ferrum container not available"
   - Solution: Start the Ferrum Docker environment

2. **Parameter Validation Failed**
   - Error: "Parameter validation failed"
   - Solution: Check parameter types and constraints

3. **Command Timeout**
   - Error: "Container execution failed"
   - Solution: Check container logs and resource availability

### Debug Mode

Enable verbose logging by setting the log level:
```bash
export LOG_LEVEL=debug
```

## Examples

### Complete Workflow Example

1. **Initialize Project**
```json
{
  "tool": "ferrum_init",
  "parameters": {
    "name": "ecommerce-api",
    "with_db": true,
    "with_auth": true,
    "api_only": true
  }
}
```

2. **Generate DSL with AI**
```json
{
  "tool": "ferrum_prompt",
  "parameters": {
    "prompt": "Create an e-commerce API with products, orders, and user management",
    "output_file": "gen/ecommerce.yaml",
    "use_patterns": true
  }
}
```

3. **Compile DSL**
```json
{
  "tool": "ferrum_compile",
  "parameters": {
    "files": ["gen/ecommerce.yaml"],
    "output_dir": "./ecommerce-api"
  }
}
```

4. **Start Development**
```json
{
  "tool": "ferrum_dev",
  "parameters": {
    "project_path": "./ecommerce-api",
    "with_ai": true
  }
}
```

This workflow demonstrates the complete cycle from project initialization to running development environment, all through MCP tools that can be called from IDEs like Kiro.