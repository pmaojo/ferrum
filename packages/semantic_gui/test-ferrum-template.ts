/**
 * Test Ferrum SCG Template Integration
 */

import { readFileSync } from 'fs';
import { FerrumGraphData, validateFerrumGraphData } from './shared/types/ferrum-types';

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function runTemplateTests() {
  console.log('🧪 Running Ferrum Template Integration Tests...\n');

  // Test 1: Load and validate template
  console.log('Test 1: Load and validate ferrus-hexagonal template');
  const templateContent = readFileSync('templates/ferrus-hexagonal.json', 'utf8');
  const template = JSON.parse(templateContent);
  
  assert(template.id === 'ferrus-hexagonal', 'Template should have correct ID');
  assert(template.nodeTypes.length === 9, 'Template should have 9 node types including IoT');
  assert(template.validationRules.length === 10, 'Template should have 10 validation rules including IoT rules');
  assert(template.dragAndDrop.enabled === true, 'Drag and drop should be enabled');
  
  // Check IoT node type exists
  const iotNodeType = template.nodeTypes.find((nt: any) => nt.type === 'iot');
  assert(iotNodeType !== undefined, 'IoT node type should exist');
  assert(iotNodeType.color === '#EC4899', 'IoT node should have correct color');
  assert(iotNodeType.icon === '🔗', 'IoT node should have correct icon');
  
  console.log('✅ Template validation passed\n');

  // Test 2: Create sample graph data using template node types
  console.log('Test 2: Create sample graph data using template node types');
  
  const sampleGraphData: FerrumGraphData = {
    framework: 'ferrum',
    version: '1.0.0',
    nodes: [
      {
        id: 'module1',
        type: 'module',
        position: { x: 0, y: 0 },
        data: {
          fields: { name: 'IoTModule' }
        }
      },
      {
        id: 'iot1',
        type: 'iot',
        position: { x: 300, y: 150 },
        data: {
          protocol: 'gpio',
          driver: 'rppal',
          expose: {
            method: 'POST',
            path: '/api/blink'
          }
        }
      },
      {
        id: 'usecase1',
        type: 'usecase',
        position: { x: 50, y: 100 },
        data: {
          input: [{ name: 'command', type: 'string' }],
          output: 'Result',
          depends_on: ['iot1']
        }
      },
      {
        id: 'port1',
        type: 'port',
        position: { x: 150, y: 50 },
        data: {
          methods: [
            { name: 'execute', parameters: ['command'], returnType: 'Result' }
          ]
        }
      },
      {
        id: 'adapter1',
        type: 'adapter',
        position: { x: 200, y: 100 },
        data: {
          implements: 'port1',
          depends_on: ['iot1']
        }
      }
    ],
    edges: [
      {
        id: 'edge1',
        source: 'usecase1',
        target: 'port1',
        type: 'dependency'
      },
      {
        id: 'edge2',
        source: 'adapter1',
        target: 'port1',
        type: 'implementation'
      },
      {
        id: 'edge3',
        source: 'adapter1',
        target: 'iot1',
        type: 'dependency'
      },
      {
        id: 'edge4',
        source: 'module1',
        target: 'usecase1',
        type: 'aggregates'
      },
      {
        id: 'edge5',
        source: 'module1',
        target: 'iot1',
        type: 'aggregates'
      }
    ],
    metadata: {
      module: 'iot-module',
      created_at: '2025-01-10T00:00:00Z',
      last_modified: '2025-01-10T00:00:00Z',
      app_name: 'IoTApp',
      features: ['gpio', 'mqtt']
    }
  };

  const validation = validateFerrumGraphData(sampleGraphData);
  assert(validation.valid, 'Sample graph data should be valid');
  console.log('✅ Sample graph data validation passed\n');

  // Test 3: Verify template node types match FerrumGraphData node types
  console.log('Test 3: Verify template node types compatibility');
  
  const templateNodeTypes = template.nodeTypes.map((nt: any) => nt.type);
  const ferrumNodeTypes = ['module', 'usecase', 'adapter', 'port', 'entity', 'event', 'handler', 'service', 'iot'];
  
  ferrumNodeTypes.forEach(nodeType => {
    assert(templateNodeTypes.includes(nodeType), `Template should include ${nodeType} node type`);
  });
  
  console.log('✅ Template node types compatibility verified\n');

  // Test 4: Test drag and drop configuration
  console.log('Test 4: Verify drag and drop configuration');
  
  assert(template.dragAndDrop.enabled === true, 'Drag and drop should be enabled');
  assert(template.dragAndDrop.nodeCreation.enabled === true, 'Node creation should be enabled');
  assert(template.dragAndDrop.edgeCreation.enabled === true, 'Edge creation should be enabled');
  
  // Check allowed connections for IoT
  const iotConnections = template.dragAndDrop.edgeCreation.allowedConnections.iot;
  assert(Array.isArray(iotConnections), 'IoT should have allowed connections');
  assert(iotConnections.includes('adapter'), 'IoT should be able to connect to adapters');
  assert(iotConnections.includes('port'), 'IoT should be able to connect to ports');
  
  console.log('✅ Drag and drop configuration verified\n');

  // Test 5: Test SCG mapping configuration
  console.log('Test 5: Verify SCG mapping configuration');
  
  const scgMapping = template.connector.scgMapping;
  assert(scgMapping.nodePositioning.iot !== undefined, 'IoT node positioning should be defined');
  assert(scgMapping.componentTypes.iot === 'infrastructure', 'IoT should be mapped to infrastructure layer');
  assert(scgMapping.layerColors.infrastructure !== undefined, 'Infrastructure layer color should be defined');
  
  console.log('✅ SCG mapping configuration verified\n');

  // Test 6: Test integration configuration
  console.log('Test 6: Verify integration configuration');
  
  const integration = template.integration;
  assert(integration.ferrumGraphData.enabled === true, 'FerrumGraphData integration should be enabled');
  assert(integration.ferrumGraphData.nodeMapping.iot === 'FerrumIoTComponent', 'IoT node mapping should be correct');
  assert(integration.dslConversion.enabled === true, 'DSL conversion should be enabled');
  
  console.log('✅ Integration configuration verified\n');

  console.log('🎉 All template integration tests passed! Ferrum SCG template is working correctly.');
}

// Run the tests
try {
  runTemplateTests();
} catch (error) {
  console.error('❌ Template test failed:', error);
  process.exit(1);
}