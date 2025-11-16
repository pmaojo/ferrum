const express = require('express');
const cors = require('cors');
const winston = require('winston');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs').promises;
const WebSocket = require('ws');
const axios = require('axios');

const app = express();
const port = process.env.MCP_PORT || 8001;

// SCG Integration Configuration
const SCG_API_URL = process.env.SCG_API_URL || 'http://localhost:3000';
const SCG_WS_URL = process.env.SCG_WS_URL || 'ws://localhost:3000';

// SCG WebSocket connection for real-time updates
let scgWebSocket = null;
const scgSubscriptions = new Map(); // projectId -> subscription info

// Configure logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'mcp-server.log' })
  ]
});

// Parameter validation utilities
function validateParameters(toolName, parameters) {
  const tool = FERRUM_TOOLS[toolName];
  if (!tool) {
    throw new Error(`Unknown tool: ${toolName}`);
  }

  const schema = tool.parameters;
  const errors = [];

  // Check required parameters
  if (schema.required) {
    for (const required of schema.required) {
      if (!(required in parameters)) {
        errors.push(`Missing required parameter: ${required}`);
      }
    }
  }

  // Validate parameter types and constraints
  for (const [key, value] of Object.entries(parameters)) {
    const propSchema = schema.properties[key];
    if (!propSchema) {
      if (!schema.additionalProperties) {
        errors.push(`Unknown parameter: ${key}`);
      }
      continue;
    }

    // Type validation
    if (propSchema.type === 'string' && typeof value !== 'string') {
      errors.push(`Parameter ${key} must be a string`);
    } else if (propSchema.type === 'boolean' && typeof value !== 'boolean') {
      errors.push(`Parameter ${key} must be a boolean`);
    } else if (propSchema.type === 'integer' && !Number.isInteger(value)) {
      errors.push(`Parameter ${key} must be an integer`);
    } else if (propSchema.type === 'array' && !Array.isArray(value)) {
      errors.push(`Parameter ${key} must be an array`);
    }

    // Additional constraints
    if (propSchema.pattern && typeof value === 'string') {
      const regex = new RegExp(propSchema.pattern);
      if (!regex.test(value)) {
        errors.push(`Parameter ${key} does not match required pattern`);
      }
    }

    if (propSchema.enum && !propSchema.enum.includes(value)) {
      errors.push(`Parameter ${key} must be one of: ${propSchema.enum.join(', ')}`);
    }

    if (propSchema.minimum !== undefined && value < propSchema.minimum) {
      errors.push(`Parameter ${key} must be at least ${propSchema.minimum}`);
    }

    if (propSchema.maximum !== undefined && value > propSchema.maximum) {
      errors.push(`Parameter ${key} must be at most ${propSchema.maximum}`);
    }

    if (propSchema.minLength !== undefined && typeof value === 'string' && value.length < propSchema.minLength) {
      errors.push(`Parameter ${key} must be at least ${propSchema.minLength} characters long`);
    }
  }

  if (errors.length > 0) {
    throw new Error(`Parameter validation failed: ${errors.join(', ')}`);
  }

  return true;
}

// Apply default values to parameters
function applyDefaults(toolName, parameters) {
  const tool = FERRUM_TOOLS[toolName];
  const result = { ...parameters };
  
  for (const [key, propSchema] of Object.entries(tool.parameters.properties)) {
    if (!(key in result) && propSchema.default !== undefined) {
      result[key] = propSchema.default;
    }
  }
  
  return result;
}

// Docker container execution helper with context awareness
function executeInFerrumContainer(command, workingDir = '/workspace', options = {}) {
  return new Promise((resolve, reject) => {
    const containerName = process.env.FERRUM_CONTAINER_NAME || 'ferrum_cli';
    const timeout = options.timeout || 300000; // 5 minutes default
    
    // Build Docker command with proper escaping
    const dockerCommand = `docker exec -w ${workingDir} ${containerName} sh -c "${command.replace(/"/g, '\\"')}"`;
    
    logger.info(`Executing in Ferrum container (${containerName}): ${command}`, {
      workingDir,
      timeout,
      containerName
    });
    
    const execOptions = {
      timeout,
      maxBuffer: 1024 * 1024 * 10, // 10MB buffer
      env: {
        ...process.env,
        DOCKER_HOST: process.env.DOCKER_HOST || 'unix:///var/run/docker.sock'
      }
    };
    
    exec(dockerCommand, execOptions, (error, stdout, stderr) => {
      if (error) {
        logger.error(`Container execution failed: ${error.message}`, {
          command,
          containerName,
          workingDir,
          exitCode: error.code,
          signal: error.signal
        });
        
        // Provide more specific error messages
        if (error.message.includes('No such container')) {
          reject(new Error(`Ferrum container '${containerName}' not found. Please start the Ferrum environment.`));
        } else if (error.message.includes('timeout')) {
          reject(new Error(`Command timed out after ${timeout}ms. The operation may be too complex.`));
        } else {
          reject(new Error(`Container execution failed: ${error.message}`));
        }
        return;
      }
      
      if (stderr && !stderr.includes('warning')) {
        logger.warn(`Container stderr: ${stderr}`, { command, containerName });
      }
      
      resolve({
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        success: true,
        containerName,
        workingDir
      });
    });
  });
}

// Enhanced container health check with detailed status
async function checkFerrumContainer() {
  return new Promise((resolve) => {
    const containerName = process.env.FERRUM_CONTAINER_NAME || 'ferrum_cli';
    
    exec(`docker inspect ${containerName} --format '{{.State.Status}}'`, (error, stdout) => {
      if (error) {
        logger.debug(`Container check failed: ${error.message}`);
        resolve({
          running: false,
          status: 'not_found',
          containerName,
          message: `Container '${containerName}' not found`
        });
      } else {
        const status = stdout.trim();
        const running = status === 'running';
        
        resolve({
          running,
          status,
          containerName,
          message: running ? 'Container is running' : `Container status: ${status}`
        });
      }
    });
  });
}

// Get container resource usage
async function getContainerStats() {
  return new Promise((resolve) => {
    const containerName = process.env.FERRUM_CONTAINER_NAME || 'ferrum_cli';
    
    exec(`docker stats ${containerName} --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"`, (error, stdout) => {
      if (error) {
        resolve(null);
      } else {
        const lines = stdout.trim().split('\n');
        if (lines.length > 1) {
          const stats = lines[1].split('\t');
          resolve({
            cpu: stats[0],
            memory: stats[1],
            network: stats[2],
            disk: stats[3]
          });
        } else {
          resolve(null);
        }
      }
    });
  });
}

// Context-aware project path resolution
function resolveProjectPath(relativePath, containerWorkspace = '/workspace') {
  if (relativePath.startsWith('/')) {
    return relativePath; // Absolute path
  }
  
  // Resolve relative to container workspace
  return path.posix.join(containerWorkspace, relativePath);
}

// Enhanced file operations in container
async function readFileFromContainer(filePath, containerWorkspace = '/workspace') {
  const resolvedPath = resolveProjectPath(filePath, containerWorkspace);
  
  try {
    const result = await executeInFerrumContainer(`cat "${resolvedPath}"`, containerWorkspace);
    return result.stdout;
  } catch (error) {
    throw new Error(`Failed to read file ${filePath}: ${error.message}`);
  }
}

async function writeFileToContainer(filePath, content, containerWorkspace = '/workspace') {
  const resolvedPath = resolveProjectPath(filePath, containerWorkspace);
  
  // Escape content for shell
  const escapedContent = content.replace(/'/g, "'\"'\"'");
  
  try {
    await executeInFerrumContainer(`echo '${escapedContent}' > "${resolvedPath}"`, containerWorkspace);
    return true;
  } catch (error) {
    throw new Error(`Failed to write file ${filePath}: ${error.message}`);
  }
}

// Check if file exists in container
async function fileExistsInContainer(filePath, containerWorkspace = '/workspace') {
  const resolvedPath = resolveProjectPath(filePath, containerWorkspace);
  
  try {
    await executeInFerrumContainer(`test -f "${resolvedPath}"`, containerWorkspace);
    return true;
  } catch (error) {
    return false;
  }
}

// SCG Integration Functions
function initializeSCGConnection() {
  if (scgWebSocket && scgWebSocket.readyState === WebSocket.OPEN) {
    return;
  }

  try {
    scgWebSocket = new WebSocket(SCG_WS_URL);
    
    scgWebSocket.on('open', () => {
      logger.info('Connected to SCG WebSocket', { url: SCG_WS_URL });
    });
    
    scgWebSocket.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        logger.debug('Received SCG WebSocket message', { type: message.type });
      } catch (error) {
        logger.error('Failed to parse SCG WebSocket message', error);
      }
    });
    
    scgWebSocket.on('close', () => {
      logger.warn('SCG WebSocket connection closed, attempting reconnect in 5s');
      setTimeout(initializeSCGConnection, 5000);
    });
    
    scgWebSocket.on('error', (error) => {
      logger.error('SCG WebSocket error', error);
    });
  } catch (error) {
    logger.error('Failed to initialize SCG WebSocket connection', error);
    setTimeout(initializeSCGConnection, 5000);
  }
}

// Send real-time update to SCG
function sendSCGUpdate(projectId, updateType, data) {
  if (!scgWebSocket || scgWebSocket.readyState !== WebSocket.OPEN) {
    logger.warn('SCG WebSocket not connected, skipping update', { projectId, updateType });
    return;
  }

  const message = {
    type: 'mcp-tool-update',
    projectId,
    updateType,
    data,
    timestamp: new Date().toISOString(),
    source: 'ferrum-mcp'
  };

  try {
    scgWebSocket.send(JSON.stringify(message));
    logger.debug('Sent SCG update', { projectId, updateType });
  } catch (error) {
    logger.error('Failed to send SCG update', error);
  }
}

// Subscribe to project updates in SCG
async function subscribeSCGProject(projectId, userId = 'mcp-server') {
  if (!scgWebSocket || scgWebSocket.readyState !== WebSocket.OPEN) {
    logger.warn('Cannot subscribe to SCG project - WebSocket not connected', { projectId });
    return false;
  }

  const subscribeMessage = {
    type: 'subscribe',
    projectId,
    userId,
    userName: 'MCP Server',
    userEmail: 'mcp@ferrum.dev'
  };

  try {
    scgWebSocket.send(JSON.stringify(subscribeMessage));
    scgSubscriptions.set(projectId, {
      projectId,
      userId,
      subscribedAt: new Date().toISOString()
    });
    logger.info('Subscribed to SCG project', { projectId });
    return true;
  } catch (error) {
    logger.error('Failed to subscribe to SCG project', error);
    return false;
  }
}

// Convert Ferrum project data to SCG graph format
async function convertToSCGGraph(projectPath, projectName) {
  try {
    // Try to read the generated DSL file
    const dslFiles = ['grafo.yaml', 'gen/example.yaml', `gen/${projectName}.yaml`];
    let dslContent = null;
    
    for (const dslFile of dslFiles) {
      try {
        dslContent = await readFileFromContainer(dslFile, projectPath);
        break;
      } catch (error) {
        // Continue to next file
      }
    }

    if (!dslContent) {
      logger.warn('No DSL file found for SCG conversion', { projectPath, projectName });
      return null;
    }

    // Convert DSL to SCG graph format using the Ferrum converter
    // This would use the ferrum-dsl-converter.ts functionality
    const graphData = {
      framework: 'ferrum',
      version: '1.0.0',
      nodes: [],
      edges: [],
      metadata: {
        project_name: projectName,
        project_path: projectPath,
        generated_at: new Date().toISOString(),
        source: 'mcp-tool'
      }
    };

    // Parse the DSL content and extract nodes/edges
    // This is a simplified version - in production, this would use the actual converter
    const lines = dslContent.split('\n');
    let currentNode = null;
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('- name:')) {
        const name = trimmed.replace('- name:', '').trim();
        currentNode = {
          id: name.toLowerCase().replace(/\s+/g, '_'),
          type: 'usecase', // Default type
          position: { x: Math.random() * 800, y: Math.random() * 600 },
          data: {
            name,
            input: [],
            output: null,
            depends_on: []
          }
        };
        graphData.nodes.push(currentNode);
      } else if (trimmed.startsWith('input:') && currentNode) {
        // Parse input parameters
      } else if (trimmed.startsWith('output:') && currentNode) {
        currentNode.data.output = trimmed.replace('output:', '').trim();
      }
    }

    return graphData;
  } catch (error) {
    logger.error('Failed to convert project to SCG graph', error);
    return null;
  }
}

// Send project update to SCG
async function updateSCGProject(projectId, projectData) {
  try {
    const response = await axios.post(`${SCG_API_URL}/api/projects/${projectId}/graph`, {
      graphData: projectData,
      source: 'ferrum-mcp',
      timestamp: new Date().toISOString()
    });
    
    logger.info('Updated SCG project', { projectId, status: response.status });
    return true;
  } catch (error) {
    logger.error('Failed to update SCG project', error);
    return false;
  }
}

// Send tool execution status to SCG
function sendToolExecutionStatus(projectId, toolName, status, data = {}) {
  sendSCGUpdate(projectId, 'tool-execution', {
    tool: toolName,
    status,
    ...data
  });
}

// Send visual feedback for tool execution
function sendVisualFeedback(projectId, feedbackType, message, data = {}) {
  sendSCGUpdate(projectId, 'visual-feedback', {
    feedbackType, // 'success', 'error', 'warning', 'info', 'progress'
    message,
    ...data
  });
}

// Middleware
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    service: 'mcp-server',
    ferrum_tools_count: Object.keys(FERRUM_TOOLS).length
  });
});

// Validate tool parameters endpoint
app.post('/validate/:toolName', (req, res) => {
  const { toolName } = req.params;
  const { parameters = {} } = req.body;
  
  try {
    validateParameters(toolName, parameters);
    const finalParameters = applyDefaults(toolName, parameters);
    
    res.json({
      tool: toolName,
      valid: true,
      parameters: finalParameters,
      message: 'Parameters are valid'
    });
  } catch (error) {
    res.status(400).json({
      tool: toolName,
      valid: false,
      error: error.message,
      parameters
    });
  }
});

// Container status endpoint
app.get('/container/status', async (req, res) => {
  try {
    const containerStatus = await checkFerrumContainer();
    const stats = containerStatus.running ? await getContainerStats() : null;
    
    res.json({
      container: containerStatus,
      stats,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to check container status',
      message: error.message
    });
  }
});

// Container management endpoints
app.post('/container/start', async (req, res) => {
  try {
    const result = await new Promise((resolve, reject) => {
      exec('docker-compose -f docker-compose.ferrum.yml up -d ferrum-cli', (error, stdout, stderr) => {
        if (error) {
          reject(error);
        } else {
          resolve({ stdout, stderr });
        }
      });
    });
    
    // Wait a moment for container to start
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    const status = await checkFerrumContainer();
    
    res.json({
      action: 'start',
      success: status.running,
      container: status,
      output: result.stdout
    });
  } catch (error) {
    res.status(500).json({
      action: 'start',
      success: false,
      error: error.message
    });
  }
});

app.post('/container/stop', async (req, res) => {
  try {
    const result = await new Promise((resolve, reject) => {
      exec('docker-compose -f docker-compose.ferrum.yml stop ferrum-cli', (error, stdout, stderr) => {
        if (error) {
          reject(error);
        } else {
          resolve({ stdout, stderr });
        }
      });
    });
    
    const status = await checkFerrumContainer();
    
    res.json({
      action: 'stop',
      success: !status.running,
      container: status,
      output: result.stdout
    });
  } catch (error) {
    res.status(500).json({
      action: 'stop',
      success: false,
      error: error.message
    });
  }
});

// File operations endpoints for container integration
app.get('/container/files/*', async (req, res) => {
  try {
    const filePath = req.params[0];
    const content = await readFileFromContainer(filePath);
    
    res.json({
      file: filePath,
      content,
      size: content.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(404).json({
      error: 'File not found or not accessible',
      file: req.params[0],
      message: error.message
    });
  }
});

app.post('/container/files/*', async (req, res) => {
  try {
    const filePath = req.params[0];
    const { content } = req.body;
    
    if (!content) {
      return res.status(400).json({
        error: 'Content is required',
        file: filePath
      });
    }
    
    await writeFileToContainer(filePath, content);
    
    res.json({
      file: filePath,
      action: 'write',
      success: true,
      size: content.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to write file',
      file: req.params[0],
      message: error.message
    });
  }
});

// Project listing endpoint
app.get('/container/projects', async (req, res) => {
  try {
    const result = await executeInFerrumContainer('find /workspace -maxdepth 2 -name "Cargo.toml" -exec dirname {} \\;');
    const projects = result.stdout.split('\n')
      .filter(line => line.trim())
      .map(projectPath => {
        const name = path.basename(projectPath);
        return {
          name,
          path: projectPath,
          relative_path: projectPath.replace('/workspace/', '')
        };
      });
    
    res.json({
      projects,
      count: projects.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to list projects',
      message: error.message,
      projects: []
    });
  }
});

// Ferrum MCP Tool Definitions
const FERRUM_TOOLS = {
  ferrum_init: {
    name: 'ferrum_init',
    description: 'Initialize a new Ferrum project with specified features and configuration',
    parameters: {
      type: 'object',
      properties: {
        name: {
          type: 'string',
          description: 'Project name (required)',
          pattern: '^[a-zA-Z][a-zA-Z0-9_-]*$'
        },
        with_graph: {
          type: 'boolean',
          description: 'Include graph database support (Neo4j)',
          default: false
        },
        with_ai: {
          type: 'boolean',
          description: 'Include AI/LLM integration features',
          default: false
        },
        with_db: {
          type: 'boolean',
          description: 'Include Diesel ORM setup for PostgreSQL',
          default: false
        },
        with_auth: {
          type: 'boolean',
          description: 'Include authentication templates',
          default: false
        },
        with_jobs: {
          type: 'boolean',
          description: 'Include background job templates',
          default: false
        },
        with_uploads: {
          type: 'boolean',
          description: 'Include file upload templates',
          default: false
        },
        frontend: {
          type: 'string',
          description: 'Frontend framework choice',
          enum: ['react', 'leptos-csr', 'leptos-ssr'],
          default: 'react'
        },
        api_only: {
          type: 'boolean',
          description: 'Backend only project (no frontend)',
          default: false
        },
        interactive: {
          type: 'boolean',
          description: 'Use interactive mode for configuration',
          default: false
        }
      },
      required: ['name'],
      additionalProperties: false
    },
    examples: [
      {
        name: 'my-ferrum-app',
        with_graph: true,
        with_ai: true,
        frontend: 'react'
      },
      {
        name: 'api-service',
        api_only: true,
        with_db: true,
        with_auth: true
      }
    ]
  },

  ferrum_compile: {
    name: 'ferrum_compile',
    description: 'Compile Ferrum DSL files to generate code with automatic PermaGraph sync',
    parameters: {
      type: 'object',
      properties: {
        files: {
          type: 'array',
          items: { type: 'string' },
          description: 'DSL files to compile (supports glob patterns)',
          default: ['gen/*.yaml']
        },
        output_dir: {
          type: 'string',
          description: 'Output directory for generated code',
          default: '.'
        },
        templates_dir: {
          type: 'string',
          description: 'Templates directory path',
          default: 'templates'
        },
        module: {
          type: 'string',
          description: 'Specific module to compile (optional)'
        },
        graph_mode: {
          type: 'boolean',
          description: 'Enable graph mode compilation',
          default: false
        },
        threads: {
          type: 'integer',
          description: 'Number of threads for parallel compilation',
          minimum: 1,
          maximum: 16
        },
        dry_run: {
          type: 'boolean',
          description: 'Perform dry run without writing files',
          default: false
        }
      },
      required: ['files'],
      additionalProperties: false
    },
    examples: [
      {
        files: ['gen/users.yaml'],
        output_dir: '.',
        graph_mode: false
      },
      {
        files: ['gen/*.yaml'],
        module: 'auth',
        threads: 4
      }
    ]
  },

  ferrum_prompt: {
    name: 'ferrum_prompt',
    description: 'Generate Ferrum DSL from natural language using AI with GraphRAG context',
    parameters: {
      type: 'object',
      properties: {
        prompt: {
          type: 'string',
          description: 'Natural language description of the desired architecture',
          minLength: 10
        },
        output_file: {
          type: 'string',
          description: 'Output file for generated DSL',
          default: 'grafo.yaml'
        },
        context_project: {
          type: 'string',
          description: 'Path to existing project for context (optional)'
        },
        use_patterns: {
          type: 'boolean',
          description: 'Use GraphRAG patterns for enhanced generation',
          default: true
        },
        ai_model: {
          type: 'string',
          description: 'AI model to use for generation',
          enum: ['gpt-4', 'gpt-3.5-turbo', 'claude-3', 'local-llm'],
          default: 'gpt-4'
        }
      },
      required: ['prompt'],
      additionalProperties: false
    },
    examples: [
      {
        prompt: 'Create a user management system with authentication and profile management',
        use_patterns: true,
        output_file: 'gen/user_system.yaml'
      },
      {
        prompt: 'Build an e-commerce API with products, orders, and payments',
        context_project: './existing-project',
        ai_model: 'claude-3'
      }
    ]
  },

  ferrum_doctor: {
    name: 'ferrum_doctor',
    description: 'Diagnose Ferrum project health and dependencies',
    parameters: {
      type: 'object',
      properties: {
        project_path: {
          type: 'string',
          description: 'Path to Ferrum project to diagnose',
          default: '.'
        },
        check_dependencies: {
          type: 'boolean',
          description: 'Check system dependencies (Rust, Node.js, etc.)',
          default: true
        },
        check_services: {
          type: 'boolean',
          description: 'Check external services (database, AI, etc.)',
          default: true
        },
        verbose: {
          type: 'boolean',
          description: 'Verbose output with detailed diagnostics',
          default: false
        }
      },
      additionalProperties: false
    },
    examples: [
      {
        project_path: '.',
        check_dependencies: true,
        check_services: true
      }
    ]
  },

  ferrum_dev: {
    name: 'ferrum_dev',
    description: 'Start Ferrum development environment with hot reloading',
    parameters: {
      type: 'object',
      properties: {
        project_path: {
          type: 'string',
          description: 'Path to Ferrum project',
          default: '.'
        },
        port: {
          type: 'integer',
          description: 'Backend port',
          default: 3000,
          minimum: 1024,
          maximum: 65535
        },
        frontend_port: {
          type: 'integer',
          description: 'Frontend port',
          default: 5173,
          minimum: 1024,
          maximum: 65535
        },
        with_graph: {
          type: 'boolean',
          description: 'Start with graph database',
          default: false
        },
        with_ai: {
          type: 'boolean',
          description: 'Start with AI services',
          default: false
        },
        detached: {
          type: 'boolean',
          description: 'Run in detached mode',
          default: false
        }
      },
      additionalProperties: false
    },
    examples: [
      {
        project_path: '.',
        with_graph: true,
        with_ai: true
      }
    ]
  }
};

// MCP tools endpoint with comprehensive Ferrum tool definitions
app.get('/tools', (req, res) => {
  const tools = Object.values(FERRUM_TOOLS).map(tool => ({
    name: tool.name,
    description: tool.description,
    inputSchema: tool.parameters
  }));

  res.json({
    tools,
    _metadata: {
      framework: 'ferrum',
      version: '1.0.0',
      capabilities: [
        'project_initialization',
        'dsl_compilation',
        'ai_generation',
        'development_environment',
        'health_diagnostics'
      ]
    }
  });
});

// Get specific tool definition
app.get('/tools/:toolName', (req, res) => {
  const { toolName } = req.params;
  const tool = FERRUM_TOOLS[toolName];
  
  if (!tool) {
    return res.status(404).json({
      error: 'Tool not found',
      available_tools: Object.keys(FERRUM_TOOLS)
    });
  }

  res.json({
    tool,
    usage_examples: tool.examples || []
  });
});

// Tool execution endpoint with proper Ferrum integration
app.post('/execute/:toolName', async (req, res) => {
  const { toolName } = req.params;
  const { parameters = {} } = req.body;
  
  try {
    // Validate tool exists
    if (!FERRUM_TOOLS[toolName]) {
      return res.status(400).json({
        error: 'Unknown tool',
        tool: toolName,
        available_tools: Object.keys(FERRUM_TOOLS)
      });
    }

    // Validate parameters
    validateParameters(toolName, parameters);
    
    // Apply default values
    const finalParameters = applyDefaults(toolName, parameters);
    
    logger.info(`Executing Ferrum tool: ${toolName}`, { parameters: finalParameters });

    // Check if Ferrum container is available
    const containerStatus = await checkFerrumContainer();
    if (!containerStatus.running) {
      return res.status(503).json({
        error: 'Ferrum container not available',
        message: containerStatus.message,
        status: containerStatus.status,
        container_name: containerStatus.containerName,
        suggestion: 'Run: docker-compose -f docker-compose.ferrum.yml up -d'
      });
    }

    // Determine project ID for SCG integration
    const projectId = finalParameters.name || finalParameters.project_path || 'default-project';
    
    // Send initial execution status to SCG
    sendToolExecutionStatus(projectId, toolName, 'started', { parameters: finalParameters });
    sendVisualFeedback(projectId, 'info', `Starting ${toolName}...`, { tool: toolName });

    // Execute the specific tool
    let result;
    try {
      switch (toolName) {
        case 'ferrum_init':
          result = await executeFerrumInit(finalParameters);
          break;
        case 'ferrum_compile':
          result = await executeFerrumCompile(finalParameters);
          break;
        case 'ferrum_prompt':
          result = await executeFerrumPrompt(finalParameters);
          break;
        case 'ferrum_doctor':
          result = await executeFerrumDoctor(finalParameters);
          break;
        case 'ferrum_dev':
          result = await executeFerrumDev(finalParameters);
          break;
        default:
          throw new Error(`Tool execution not implemented: ${toolName}`);
      }
      
      // Send success status to SCG
      sendToolExecutionStatus(projectId, toolName, 'completed', { result });
      sendVisualFeedback(projectId, 'success', `${toolName} completed successfully`, { 
        tool: toolName,
        result: result
      });
      
    } catch (toolError) {
      // Send error status to SCG
      sendToolExecutionStatus(projectId, toolName, 'failed', { error: toolError.message });
      sendVisualFeedback(projectId, 'error', `${toolName} failed: ${toolError.message}`, { 
        tool: toolName,
        error: toolError.message
      });
      throw toolError;
    }

    res.json({
      tool: toolName,
      status: 'success',
      result,
      parameters: finalParameters,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    logger.error(`Tool execution failed: ${toolName}`, { error: error.message, parameters });
    
    res.status(400).json({
      tool: toolName,
      status: 'error',
      error: error.message,
      parameters,
      timestamp: new Date().toISOString()
    });
  }
});

// Ferrum tool execution functions with enhanced error handling
async function executeFerrumInit(params) {
  const {
    name,
    with_graph,
    with_ai,
    with_db,
    with_auth,
    with_jobs,
    with_uploads,
    frontend,
    api_only,
    interactive
  } = params;

  // Build command with proper flag handling
  let command = `ferrum init ${name}`;
  
  if (with_graph) command += ' --with-graph';
  if (with_ai) command += ' --with-ai';
  if (with_db) command += ' --with-db';
  if (with_auth) command += ' --with-auth';
  if (with_jobs) command += ' --with-jobs';
  if (with_uploads) command += ' --with-uploads';
  if (api_only) command += ' --api-only';
  if (!interactive) command += ' --no-interactive'; // Default to non-interactive in container
  
  if (frontend !== 'react') {
    command += ` --frontend ${frontend}`;
  }

  // Execute with extended timeout for project initialization
  const result = await executeInFerrumContainer(command, '/workspace', { timeout: 600000 }); // 10 minutes
  
  // Check if project was actually created
  const projectPath = `/workspace/${name}`;
  const projectExists = await fileExistsInContainer(`${name}/Cargo.toml`, '/workspace');
  
  if (!projectExists) {
    throw new Error('Project initialization failed - project directory not created');
  }

  // Try to read the generated example file
  let exampleContent = null;
  try {
    exampleContent = await readFileFromContainer(`${name}/gen/example.yaml`, '/workspace');
  } catch (error) {
    logger.warn(`Could not read example.yaml: ${error.message}`);
  }
  
  // Convert project to SCG graph format and update SCG
  const projectId = name;
  try {
    await subscribeSCGProject(projectId);
    
    const graphData = await convertToSCGGraph(`/workspace/${name}`, name);
    if (graphData) {
      await updateSCGProject(projectId, graphData);
      sendVisualFeedback(projectId, 'success', 'Project structure loaded in visual editor', {
        nodeCount: graphData.nodes.length,
        edgeCount: graphData.edges.length
      });
    }
  } catch (scgError) {
    logger.warn('Failed to update SCG with new project', scgError);
  }
  
  return {
    project_name: name,
    project_path: `./${name}`,
    container_path: projectPath,
    features_enabled: {
      graph: with_graph,
      ai: with_ai,
      database: with_db,
      auth: with_auth,
      jobs: with_jobs,
      uploads: with_uploads
    },
    frontend_framework: frontend,
    api_only,
    project_created: projectExists,
    example_dsl: exampleContent ? exampleContent.substring(0, 500) : null,
    output: result.stdout,
    next_steps: [
      `cd ${name}`,
      'ferrum compile gen/example.yaml',
      'ferrum dev'
    ],
    docker_commands: [
      `docker exec -it ferrum_cli sh -c "cd /workspace/${name} && ferrum compile gen/example.yaml"`,
      `docker exec -it ferrum_cli sh -c "cd /workspace/${name} && ferrum dev"`
    ]
  };
}

async function executeFerrumCompile(params) {
  const {
    files,
    output_dir,
    templates_dir,
    module,
    graph_mode,
    threads,
    dry_run
  } = params;

  // Validate input files exist
  for (const file of files) {
    const exists = await fileExistsInContainer(file, '/workspace');
    if (!exists) {
      throw new Error(`DSL file not found: ${file}`);
    }
  }

  let command = `ferrum compile ${files.join(' ')}`;
  
  if (output_dir !== '.') command += ` --output ${output_dir}`;
  if (templates_dir !== 'templates') command += ` --templates ${templates_dir}`;
  if (module) command += ` --module ${module}`;
  if (graph_mode) command += ' --graph';
  if (threads) command += ` --threads ${threads}`;
  if (dry_run) command += ' --dry-run';

  // Execute with timeout based on number of files
  const timeout = Math.max(120000, files.length * 60000); // At least 2 minutes, +1 minute per file
  const result = await executeInFerrumContainer(command, '/workspace', { timeout });
  
  // Extract compilation metrics
  const generatedFiles = extractGeneratedFiles(result.stdout);
  const compilationTime = extractCompilationTime(result.stdout);
  const warnings = extractWarnings(result.stdout);
  const errors = extractErrors(result.stdout);
  
  // Check for PermaGraph sync status
  const syncStatus = extractSyncStatus(result.stdout);
  
  // Update SCG with compilation results
  const projectId = files[0].split('/')[0] || 'current-project';
  try {
    // Send compilation progress updates
    sendVisualFeedback(projectId, 'info', `Compiled ${files.length} files`, {
      generatedFiles: generatedFiles.length,
      warnings: warnings.length,
      errors: errors.length
    });
    
    // If compilation was successful, update the graph
    if (errors.length === 0 && generatedFiles.length > 0) {
      const graphData = await convertToSCGGraph('/workspace', projectId);
      if (graphData) {
        await updateSCGProject(projectId, graphData);
        sendSCGUpdate(projectId, 'graph-updated', {
          nodeCount: graphData.nodes.length,
          edgeCount: graphData.edges.length,
          generatedFiles
        });
      }
    }
    
    // Send PermaGraph sync status
    if (syncStatus !== 'unknown') {
      sendSCGUpdate(projectId, 'permagraph-sync', {
        status: syncStatus,
        timestamp: new Date().toISOString()
      });
    }
  } catch (scgError) {
    logger.warn('Failed to update SCG with compilation results', scgError);
  }
  
  return {
    compiled_files: files,
    output_directory: output_dir,
    module_filter: module,
    compilation_mode: graph_mode ? 'graph' : 'standard',
    dry_run,
    generated_files: generatedFiles,
    compilation_time: compilationTime,
    warnings: warnings.length,
    errors: errors.length,
    permagraph_sync: syncStatus,
    output: result.stdout,
    success: errors.length === 0
  };
}

async function executeFerrumPrompt(params) {
  const {
    prompt,
    output_file,
    context_project,
    use_patterns,
    ai_model
  } = params;

  const projectId = context_project || 'ai-generated-project';
  
  // Send AI generation progress to SCG
  sendVisualFeedback(projectId, 'info', 'AI is analyzing your prompt...', {
    prompt: prompt.substring(0, 100) + (prompt.length > 100 ? '...' : ''),
    ai_model,
    use_patterns
  });

  let command = `ferrum ai-enhanced-prompt "${prompt}"`;
  
  if (output_file !== 'grafo.yaml') command += ` --output ${output_file}`;
  if (context_project) command += ` --context-project ${context_project}`;
  if (!use_patterns) command += ' --no-patterns';
  if (ai_model !== 'gpt-4') command += ` --model ${ai_model}`;

  // Send generation start notification
  sendSCGUpdate(projectId, 'ai-generation', {
    status: 'generating',
    prompt,
    ai_model,
    output_file
  });

  const result = await executeInFerrumContainer(command, '/workspace', { timeout: 600000 }); // 10 minutes for AI
  
  // Read the generated DSL
  const dslPreview = await readGeneratedDSL(output_file);
  
  // Convert generated DSL to graph and update SCG
  try {
    const graphData = await convertToSCGGraph('/workspace', projectId);
    if (graphData) {
      await updateSCGProject(projectId, graphData);
      sendVisualFeedback(projectId, 'success', 'AI-generated architecture loaded in visual editor', {
        nodeCount: graphData.nodes.length,
        edgeCount: graphData.edges.length,
        generated_file: output_file
      });
      
      sendSCGUpdate(projectId, 'ai-generation', {
        status: 'completed',
        graphData,
        generated_file: output_file
      });
    }
  } catch (scgError) {
    logger.warn('Failed to update SCG with AI-generated architecture', scgError);
  }
  
  return {
    prompt,
    generated_file: output_file,
    ai_model,
    context_used: !!context_project,
    patterns_enabled: use_patterns,
    output: result.stdout,
    dsl_preview: dslPreview,
    scg_updated: true
  };
}

async function executeFerrumDoctor(params) {
  const {
    project_path,
    check_dependencies,
    check_services,
    verbose
  } = params;

  let command = `ferrum doctor`;
  
  if (project_path !== '.') command += ` --path ${project_path}`;
  if (!check_dependencies) command += ' --no-deps';
  if (!check_services) command += ' --no-services';
  if (verbose) command += ' --verbose';

  const result = await executeInFerrumContainer(command, project_path);
  
  return {
    project_path,
    health_status: extractHealthStatus(result.stdout),
    dependencies_checked: check_dependencies,
    services_checked: check_services,
    output: result.stdout,
    recommendations: extractRecommendations(result.stdout)
  };
}

async function executeFerrumDev(params) {
  const {
    project_path,
    port,
    frontend_port,
    with_graph,
    with_ai,
    detached
  } = params;

  let command = `ferrum dev`;
  
  if (port !== 3000) command += ` --port ${port}`;
  if (frontend_port !== 5173) command += ` --frontend-port ${frontend_port}`;
  if (with_graph) command += ' --with-graph';
  if (with_ai) command += ' --with-ai';
  if (detached) command += ' --detached';

  const result = await executeInFerrumContainer(command, project_path);
  
  return {
    project_path,
    backend_port: port,
    frontend_port,
    services_enabled: {
      graph: with_graph,
      ai: with_ai
    },
    detached_mode: detached,
    output: result.stdout,
    service_urls: {
      backend: `http://localhost:${port}`,
      frontend: `http://localhost:${frontend_port}`
    }
  };
}

// Helper functions for parsing command output
function extractGeneratedFiles(output) {
  const files = [];
  const lines = output.split('\n');
  
  for (const line of lines) {
    if (line.includes('Generated:') || line.includes('Created:')) {
      const match = line.match(/(?:Generated:|Created:)\s+(.+)/);
      if (match) {
        files.push(match[1].trim());
      }
    }
  }
  
  return files;
}

function extractHealthStatus(output) {
  if (output.includes('✅') || output.includes('All checks passed')) {
    return 'healthy';
  } else if (output.includes('⚠️') || output.includes('warnings')) {
    return 'warning';
  } else if (output.includes('❌') || output.includes('errors')) {
    return 'error';
  }
  return 'unknown';
}

function extractRecommendations(output) {
  const recommendations = [];
  const lines = output.split('\n');
  
  for (const line of lines) {
    if (line.includes('Recommendation:') || line.includes('Suggest:')) {
      recommendations.push(line.replace(/.*(?:Recommendation:|Suggest:)\s*/, '').trim());
    }
  }
  
  return recommendations;
}

async function readGeneratedDSL(filePath) {
  try {
    const content = await readFileFromContainer(filePath);
    return content.substring(0, 500) + (content.length > 500 ? '...' : '');
  } catch (error) {
    return 'Could not read generated DSL file';
  }
}

// Additional parsing functions for enhanced output analysis
function extractCompilationTime(output) {
  const timeMatch = output.match(/Compilation completed in (\d+(?:\.\d+)?)\s*(ms|s|minutes?)/i);
  if (timeMatch) {
    const value = parseFloat(timeMatch[1]);
    const unit = timeMatch[2].toLowerCase();
    
    // Normalize to milliseconds
    if (unit.startsWith('s')) {
      return value * 1000;
    } else if (unit.startsWith('m')) {
      return value * 60000;
    }
    return value;
  }
  return null;
}

function extractWarnings(output) {
  const warnings = [];
  const lines = output.split('\n');
  
  for (const line of lines) {
    if (line.includes('⚠️') || line.toLowerCase().includes('warning')) {
      warnings.push(line.trim());
    }
  }
  
  return warnings;
}

function extractErrors(output) {
  const errors = [];
  const lines = output.split('\n');
  
  for (const line of lines) {
    if (line.includes('❌') || line.toLowerCase().includes('error')) {
      errors.push(line.trim());
    }
  }
  
  return errors;
}

function extractSyncStatus(output) {
  if (output.includes('PermaGraph sync: success') || output.includes('✅ PermaGraph')) {
    return 'success';
  } else if (output.includes('PermaGraph sync: failed') || output.includes('❌ PermaGraph')) {
    return 'failed';
  } else if (output.includes('PermaGraph sync: in progress') || output.includes('🔄 PermaGraph')) {
    return 'in_progress';
  }
  return 'unknown';
}

// Error handling
app.use((err, req, res, next) => {
  logger.error('Server error:', err);
  res.status(500).json({ error: 'Internal server error' });
});

// SCG Integration endpoints
app.get('/scg/status', (req, res) => {
  res.json({
    scg_connected: scgWebSocket && scgWebSocket.readyState === WebSocket.OPEN,
    scg_url: SCG_WS_URL,
    subscriptions: Array.from(scgSubscriptions.values()),
    timestamp: new Date().toISOString()
  });
});

app.post('/scg/subscribe/:projectId', async (req, res) => {
  const { projectId } = req.params;
  const { userId } = req.body;
  
  try {
    const success = await subscribeSCGProject(projectId, userId);
    res.json({
      success,
      projectId,
      message: success ? 'Subscribed to SCG project' : 'Failed to subscribe'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/scg/update/:projectId', async (req, res) => {
  const { projectId } = req.params;
  const { updateType, data } = req.body;
  
  try {
    sendSCGUpdate(projectId, updateType, data);
    res.json({
      success: true,
      projectId,
      updateType,
      message: 'Update sent to SCG'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/scg/feedback/:projectId', (req, res) => {
  const { projectId } = req.params;
  const { feedbackType, message, data } = req.body;
  
  try {
    sendVisualFeedback(projectId, feedbackType, message, data);
    res.json({
      success: true,
      projectId,
      feedbackType,
      message: 'Feedback sent to SCG'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Initialize SCG connection on startup
initializeSCGConnection();

// Start server
app.listen(port, () => {
  logger.info(`MCP Server running on port ${port}`);
  logger.info(`SCG Integration: ${SCG_API_URL} (WebSocket: ${SCG_WS_URL})`);
});

module.exports = app;