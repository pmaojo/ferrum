/**
 * Ferrum DSL to Graph Converter
 * 
 * This module provides functionality to convert Ferrum YAML DSL files
 * to FerrumGraphData format for SCG visualization and vice versa.
 */

import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import {
  FerrumDSL,
  FerrumGraphData,
  FerrumGraphNode,
  FerrumGraphEdge,
  FerrumModule,
  FerrumIoTComponent,
  Position,
  validateFerrumDSL,
  validateFerrumGraphData,
} from '../types/ferrum-types';

// ============================================================================
// Configuration and Constants
// ============================================================================

/**
 * Default positioning configuration for different node types
 */
const DEFAULT_POSITIONS: Record<string, Position> = {
  module: { x: 0, y: 0 },
  usecase: { x: 150, y: 100 },
  adapter: { x: 300, y: 100 },
  port: { x: 225, y: 50 },
  entity: { x: 150, y: 200 },
  event: { x: 300, y: 200 },
  handler: { x: 75, y: 50 },
  service: { x: 375, y: 50 },
  iot: { x: 450, y: 150 },
};

/**
 * Spacing configuration for layout
 */
const LAYOUT_CONFIG = {
  moduleSpacing: { x: 500, y: 400 },
  nodeSpacing: { x: 150, y: 100 },
  gridSize: 25,
};

// ============================================================================
// YAML DSL to Graph Conversion
// ============================================================================

/**
 * Convert Ferrum YAML DSL to FerrumGraphData
 */
export function convertDslToGraph(yamlContent: string): FerrumGraphData {
  // Parse YAML
  const dsl = parseYaml(yamlContent) as FerrumDSL;
  
  // Validate DSL
  const validation = validateFerrumDSL(dsl);
  if (!validation.valid) {
    throw new Error(`Invalid Ferrum DSL: ${validation.errors?.map(e => e.message).join(', ')}`);
  }

  const nodes: FerrumGraphNode[] = [];
  const edges: FerrumGraphEdge[] = [];
  let nodeIdCounter = 0;
  let edgeIdCounter = 0;

  // Helper function to generate unique IDs
  const generateNodeId = (type: string, name: string) => `${type}_${name}_${++nodeIdCounter}`;
  const generateEdgeId = () => `edge_${++edgeIdCounter}`;

  // Track module positions for layout
  let moduleIndex = 0;
  const modulePositions = new Map<string, Position>();

  // Process modules
  if (dsl.modules) {
    Object.entries(dsl.modules).forEach(([moduleName, moduleData]) => {
      const modulePosition = {
        x: (moduleIndex % 3) * LAYOUT_CONFIG.moduleSpacing.x,
        y: Math.floor(moduleIndex / 3) * LAYOUT_CONFIG.moduleSpacing.y,
      };
      modulePositions.set(moduleName, modulePosition);

      // Create module node
      const moduleId = generateNodeId('module', moduleName);
      nodes.push({
        id: moduleId,
        type: 'module',
        position: modulePosition,
        data: {
          fields: { name: moduleName },
        },
        metadata: {
          description: `Module: ${moduleName}`,
          tags: ['module'],
        },
      });

      // Process entities
      if (moduleData.entity) {
        const entityId = generateNodeId('entity', `${moduleName}_entity`);
        const entityPosition = {
          x: modulePosition.x + DEFAULT_POSITIONS.entity.x,
          y: modulePosition.y + DEFAULT_POSITIONS.entity.y,
        };

        nodes.push({
          id: entityId,
          type: 'entity',
          position: entityPosition,
          data: {
            fields: moduleData.entity.fields || {},
            methods: Array.isArray(moduleData.entity.methods) ? moduleData.entity.methods.map(method => ({
              name: method.name,
              parameters: method.parameters ? Object.keys(method.parameters) : [],
              returnType: method.returnType,
            })) : [],
          },
          metadata: {
            description: `Entity for ${moduleName}`,
            tags: ['entity', moduleName],
          },
        });

        // Create module -> entity edge
        edges.push({
          id: generateEdgeId(),
          source: moduleId,
          target: entityId,
          type: 'aggregates',
        });
      }

      // Process use cases
      if (moduleData.usecases) {
        Object.entries(moduleData.usecases).forEach(([usecaseName, usecaseData], index) => {
          const usecaseId = generateNodeId('usecase', `${moduleName}_${usecaseName}`);
          const usecasePosition = {
            x: modulePosition.x + DEFAULT_POSITIONS.usecase.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
            y: modulePosition.y + DEFAULT_POSITIONS.usecase.y,
          };

          nodes.push({
            id: usecaseId,
            type: 'usecase',
            position: usecasePosition,
            data: {
              input: usecaseData.input || [],
              output: usecaseData.output,
              depends_on: usecaseData.depends_on || [],
              implements: usecaseData.implements,
              code: usecaseData.code,
            },
            metadata: {
              description: `Use case: ${usecaseName}`,
              tags: ['usecase', moduleName],
            },
          });

          // Create module -> usecase edge
          edges.push({
            id: generateEdgeId(),
            source: moduleId,
            target: usecaseId,
            type: 'aggregates',
          });

          // Create dependency edges
          if (usecaseData.depends_on) {
            usecaseData.depends_on.forEach(dependency => {
              // Find the dependency node (simplified - in real implementation would need better resolution)
              const dependencyNode = nodes.find(n => 
                n.data.fields?.name === dependency || 
                n.id.includes(dependency)
              );
              if (dependencyNode) {
                edges.push({
                  id: generateEdgeId(),
                  source: usecaseId,
                  target: dependencyNode.id,
                  type: 'dependency',
                });
              }
            });
          }
        });
      }

      // Process ports
      if (moduleData.ports) {
        Object.entries(moduleData.ports).forEach(([portName, portData], index) => {
          const portId = generateNodeId('port', `${moduleName}_${portName}`);
          const portPosition = {
            x: modulePosition.x + DEFAULT_POSITIONS.port.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
            y: modulePosition.y + DEFAULT_POSITIONS.port.y,
          };

          nodes.push({
            id: portId,
            type: 'port',
            position: portPosition,
            data: {
              methods: Array.isArray(portData.methods) ? portData.methods.map(method => ({
                name: method.name,
                parameters: method.parameters ? Object.keys(method.parameters) : [],
                returnType: method.returnType,
              })) : [],
            },
            metadata: {
              description: `Port: ${portName}`,
              tags: ['port', moduleName],
            },
          });

          // Create module -> port edge
          edges.push({
            id: generateEdgeId(),
            source: moduleId,
            target: portId,
            type: 'aggregates',
          });
        });
      }

      // Process adapters
      if (moduleData.adapters) {
        Object.entries(moduleData.adapters).forEach(([adapterName, adapterData], index) => {
          const adapterId = generateNodeId('adapter', `${moduleName}_${adapterName}`);
          const adapterPosition = {
            x: modulePosition.x + DEFAULT_POSITIONS.adapter.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
            y: modulePosition.y + DEFAULT_POSITIONS.adapter.y,
          };

          nodes.push({
            id: adapterId,
            type: 'adapter',
            position: adapterPosition,
            data: {
              implements: adapterData.implements,
              depends_on: adapterData.depends_on || [],
              code: adapterData.code,
            },
            metadata: {
              description: `Adapter: ${adapterName}`,
              tags: ['adapter', moduleName],
            },
          });

          // Create module -> adapter edge
          edges.push({
            id: generateEdgeId(),
            source: moduleId,
            target: adapterId,
            type: 'aggregates',
          });

          // Create implementation edge to port
          if (adapterData.implements) {
            const portNode = nodes.find(n => 
              n.type === 'port' && 
              (n.data.fields?.name === adapterData.implements || n.id.includes(adapterData.implements))
            );
            if (portNode) {
              edges.push({
                id: generateEdgeId(),
                source: adapterId,
                target: portNode.id,
                type: 'implementation',
              });
            }
          }
        });
      }

      // Process services
      if (moduleData.services) {
        Object.entries(moduleData.services).forEach(([serviceName, serviceData], index) => {
          const serviceId = generateNodeId('service', `${moduleName}_${serviceName}`);
          const servicePosition = {
            x: modulePosition.x + DEFAULT_POSITIONS.service.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
            y: modulePosition.y + DEFAULT_POSITIONS.service.y,
          };

          nodes.push({
            id: serviceId,
            type: 'service',
            position: servicePosition,
            data: serviceData,
            metadata: {
              description: `Service: ${serviceName}`,
              tags: ['service', moduleName],
            },
          });

          // Create module -> service edge
          edges.push({
            id: generateEdgeId(),
            source: moduleId,
            target: serviceId,
            type: 'aggregates',
          });
        });
      }

      // Process handlers
      if (moduleData.handlers) {
        Object.entries(moduleData.handlers).forEach(([handlerName, handlerData], index) => {
          const handlerId = generateNodeId('handler', `${moduleName}_${handlerName}`);
          const handlerPosition = {
            x: modulePosition.x + DEFAULT_POSITIONS.handler.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
            y: modulePosition.y + DEFAULT_POSITIONS.handler.y,
          };

          nodes.push({
            id: handlerId,
            type: 'handler',
            position: handlerPosition,
            data: handlerData,
            metadata: {
              description: `Handler: ${handlerName}`,
              tags: ['handler', moduleName],
            },
          });

          // Create module -> handler edge
          edges.push({
            id: generateEdgeId(),
            source: moduleId,
            target: handlerId,
            type: 'aggregates',
          });
        });
      }

      moduleIndex++;
    });
  }

  // Process IoT components
  if (dsl.iot) {
    dsl.iot.forEach((iotComponent, index) => {
      const iotId = generateNodeId('iot', iotComponent.name);
      const iotPosition = {
        x: DEFAULT_POSITIONS.iot.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
        y: DEFAULT_POSITIONS.iot.y,
      };

      nodes.push({
        id: iotId,
        type: 'iot',
        position: iotPosition,
        data: {
          protocol: iotComponent.protocol,
          driver: iotComponent.driver,
          expose: iotComponent.expose,
          code: iotComponent.code,
        },
        metadata: {
          description: `IoT Component: ${iotComponent.name}`,
          tags: ['iot', iotComponent.protocol],
        },
      });
    });
  }

  // Create the graph data
  const graphData: FerrumGraphData = {
    framework: 'ferrum',
    version: '1.0.0',
    nodes,
    edges,
    metadata: {
      module: dsl.app.name,
      created_at: new Date().toISOString(),
      last_modified: new Date().toISOString(),
      app_name: dsl.app.name,
      features: dsl.app.features || [],
    },
  };

  // Validate the generated graph data
  const graphValidation = validateFerrumGraphData(graphData);
  if (!graphValidation.valid) {
    throw new Error(`Generated invalid graph data: ${graphValidation.errors?.map(e => `${e.path}: ${e.message}`).join(', ')}`);
  }

  return graphData;
}

// ============================================================================
// Graph to YAML DSL Conversion
// ============================================================================

/**
 * Convert FerrumGraphData back to YAML DSL
 */
export function convertGraphToDsl(graphData: FerrumGraphData): string {
  // Validate input
  const validation = validateFerrumGraphData(graphData);
  if (!validation.valid) {
    throw new Error(`Invalid graph data: ${validation.errors?.map(e => e.message).join(', ')}`);
  }

  const dsl: FerrumDSL = {
    app: {
      name: graphData.metadata.app_name || graphData.metadata.module,
      features: graphData.metadata.features || [],
    },
  };

  // Group nodes by modules
  const moduleNodes = graphData.nodes.filter(n => n.type === 'module');
  const modules: Record<string, FerrumModule> = {};

  moduleNodes.forEach(moduleNode => {
    const moduleName = moduleNode.data.fields?.name || moduleNode.id;
    const module: FerrumModule = {};

    // Find all nodes that belong to this module (connected by aggregates edges)
    const moduleChildren = graphData.edges
      .filter(e => e.source === moduleNode.id && e.type === 'aggregates')
      .map(e => graphData.nodes.find(n => n.id === e.target))
      .filter(Boolean);

    // Process entities
    const entityNodes = moduleChildren.filter(n => n?.type === 'entity');
    if (entityNodes.length > 0) {
      const entityNode = entityNodes[0]; // Assume one entity per module for simplicity
      module.entity = {
        fields: entityNode!.data.fields || {},
        methods: (entityNode!.data.methods || []).map(method => ({
          name: method.name,
          parameters: method.parameters ? method.parameters.reduce((acc, param) => {
            acc[param] = 'any'; // Default type since we don't store parameter types
            return acc;
          }, {} as Record<string, string>) : {},
          returnType: method.returnType,
        })),
      };
    }

    // Process use cases
    const usecaseNodes = moduleChildren.filter(n => n?.type === 'usecase');
    if (usecaseNodes.length > 0) {
      module.usecases = {};
      usecaseNodes.forEach(usecaseNode => {
        const usecaseName = extractNameFromId(usecaseNode!.id, 'usecase');
        module.usecases![usecaseName] = {
          input: usecaseNode!.data.input || [],
          output: usecaseNode!.data.output,
          depends_on: usecaseNode!.data.depends_on || [],
          implements: usecaseNode!.data.implements,
          code: usecaseNode!.data.code,
        };
      });
    }

    // Process ports
    const portNodes = moduleChildren.filter(n => n?.type === 'port');
    if (portNodes.length > 0) {
      module.ports = {};
      portNodes.forEach(portNode => {
        const portName = extractNameFromId(portNode!.id, 'port');
        module.ports![portName] = {
          methods: (portNode!.data.methods || []).map(method => ({
            name: method.name,
            parameters: method.parameters ? method.parameters.reduce((acc, param) => {
              acc[param] = 'any'; // Default type since we don't store parameter types
              return acc;
            }, {} as Record<string, string>) : {},
            returnType: method.returnType,
          })),
        };
      });
    }

    // Process adapters
    const adapterNodes = moduleChildren.filter(n => n?.type === 'adapter');
    if (adapterNodes.length > 0) {
      module.adapters = {};
      adapterNodes.forEach(adapterNode => {
        const adapterName = extractNameFromId(adapterNode!.id, 'adapter');
        module.adapters![adapterName] = {
          implements: adapterNode!.data.implements || '',
          depends_on: adapterNode!.data.depends_on || [],
          code: adapterNode!.data.code,
        };
      });
    }

    // Process services
    const serviceNodes = moduleChildren.filter(n => n?.type === 'service');
    if (serviceNodes.length > 0) {
      module.services = {};
      serviceNodes.forEach(serviceNode => {
        const serviceName = extractNameFromId(serviceNode!.id, 'service');
        module.services![serviceName] = serviceNode!.data;
      });
    }

    // Process handlers
    const handlerNodes = moduleChildren.filter(n => n?.type === 'handler');
    if (handlerNodes.length > 0) {
      module.handlers = {};
      handlerNodes.forEach(handlerNode => {
        const handlerName = extractNameFromId(handlerNode!.id, 'handler');
        module.handlers![handlerName] = handlerNode!.data;
      });
    }

    modules[moduleName] = module;
  });

  if (Object.keys(modules).length > 0) {
    dsl.modules = modules;
  }

  // Process IoT components
  const iotNodes = graphData.nodes.filter(n => n.type === 'iot');
  if (iotNodes.length > 0) {
    dsl.iot = iotNodes.map(iotNode => ({
      name: extractNameFromId(iotNode.id, 'iot'),
      protocol: iotNode.data.protocol || '',
      driver: iotNode.data.driver,
      expose: iotNode.data.expose,
      code: iotNode.data.code,
    }));
  }

  // Convert to YAML
  return stringifyYaml(dsl, {
    indent: 2,
    lineWidth: 100,
    minContentWidth: 0,
  });
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Extract name from generated node ID
 */
function extractNameFromId(id: string, type: string): string {
  // Remove type prefix and counter suffix
  const withoutType = id.replace(`${type}_`, '');
  const parts = withoutType.split('_');
  // Remove the last part which is the counter
  parts.pop();
  return parts.join('_') || id;
}

/**
 * Validate YAML content
 */
export function validateYamlContent(yamlContent: string): { valid: boolean; error?: string } {
  try {
    const parsed = parseYaml(yamlContent);
    const validation = validateFerrumDSL(parsed);
    return {
      valid: validation.valid,
      error: validation.errors?.map(e => e.message).join(', '),
    };
  } catch (error) {
    return {
      valid: false,
      error: error instanceof Error ? error.message : 'Unknown parsing error',
    };
  }
}

/**
 * Auto-layout nodes in the graph
 */
export function autoLayoutGraph(graphData: FerrumGraphData): FerrumGraphData {
  const layoutData = { ...graphData };
  
  // Simple grid-based layout
  const moduleNodes = layoutData.nodes.filter(n => n.type === 'module');
  
  moduleNodes.forEach((moduleNode, moduleIndex) => {
    const modulePosition = {
      x: (moduleIndex % 3) * LAYOUT_CONFIG.moduleSpacing.x,
      y: Math.floor(moduleIndex / 3) * LAYOUT_CONFIG.moduleSpacing.y,
    };
    
    moduleNode.position = modulePosition;
    
    // Layout child nodes relative to module
    const moduleChildren = layoutData.edges
      .filter(e => e.source === moduleNode.id && e.type === 'aggregates')
      .map(e => layoutData.nodes.find(n => n.id === e.target))
      .filter(Boolean);
    
    moduleChildren.forEach((childNode, childIndex) => {
      if (childNode && DEFAULT_POSITIONS[childNode.type]) {
        childNode.position = {
          x: modulePosition.x + DEFAULT_POSITIONS[childNode.type].x + 
             (childIndex % 2) * LAYOUT_CONFIG.nodeSpacing.x,
          y: modulePosition.y + DEFAULT_POSITIONS[childNode.type].y + 
             Math.floor(childIndex / 2) * LAYOUT_CONFIG.nodeSpacing.y,
        };
      }
    });
  });
  
  // Layout standalone IoT nodes
  const iotNodes = layoutData.nodes.filter(n => n.type === 'iot');
  iotNodes.forEach((iotNode, index) => {
    iotNode.position = {
      x: DEFAULT_POSITIONS.iot.x + (index * LAYOUT_CONFIG.nodeSpacing.x),
      y: DEFAULT_POSITIONS.iot.y,
    };
  });
  
  return layoutData;
}