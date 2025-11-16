/**
 * Simple validation test for Ferrum types
 */

import {
  FerrumGraphData,
  FerrumDSL,
  validateFerrumGraphData,
  validateFerrumDSL,
  serializeFerrumGraphData,
  deserializeFerrumGraphData,
  serializeFerrumDSL,
  deserializeFerrumDSL,
  isFerrumGraphData,
  isFerrumDSL,
} from './shared/types/ferrum-types';

function assert(condition: boolean, message: string) {
  if (!condition) {
    throw new Error(`Assertion failed: ${message}`);
  }
}

function runTests() {
  console.log('🧪 Running Ferrum Types Tests...\n');

  // Test 1: Valid FerrumGraphData
  console.log('Test 1: Valid FerrumGraphData validation');
  const validGraphData: FerrumGraphData = {
    framework: 'ferrum',
    version: '1.0.0',
    nodes: [
      {
        id: 'node1',
        type: 'module',
        position: { x: 0, y: 0 },
        data: {
          fields: { name: 'string' },
        },
      },
      {
        id: 'node2',
        type: 'usecase',
        position: { x: 100, y: 100 },
        data: {
          input: [{ name: 'param1', type: 'string' }],
          output: 'Result',
          depends_on: ['node1'],
        },
      },
    ],
    edges: [
      {
        id: 'edge1',
        source: 'node2',
        target: 'node1',
        type: 'dependency',
      },
    ],
    metadata: {
      module: 'test-module',
      created_at: '2025-01-10T00:00:00Z',
      last_modified: '2025-01-10T00:00:00Z',
      app_name: 'TestApp',
    },
  };

  const graphValidation = validateFerrumGraphData(validGraphData);
  assert(graphValidation.valid, 'Valid graph data should pass validation');
  assert(isFerrumGraphData(validGraphData), 'Type guard should identify valid graph data');
  console.log('✅ Valid graph data validation passed\n');

  // Test 2: Invalid FerrumGraphData
  console.log('Test 2: Invalid FerrumGraphData validation');
  const invalidGraphData = {
    framework: 'invalid',
    version: '1.0.0',
    nodes: [],
    edges: [],
    metadata: {},
  };

  const invalidGraphValidation = validateFerrumGraphData(invalidGraphData);
  assert(!invalidGraphValidation.valid, 'Invalid graph data should fail validation');
  assert(!isFerrumGraphData(invalidGraphData), 'Type guard should reject invalid graph data');
  assert(invalidGraphValidation.errors && invalidGraphValidation.errors.length > 0, 'Should have validation errors');
  console.log('✅ Invalid graph data validation passed\n');

  // Test 3: Valid FerrumDSL
  console.log('Test 3: Valid FerrumDSL validation');
  const validDSL: FerrumDSL = {
    app: {
      name: 'TestApp',
      features: ['auth', 'graphql'],
    },
    modules: {
      users: {
        entity: {
          fields: {
            email: 'string',
            password: 'string',
          },
        },
        usecases: {
          createUser: {
            input: [
              { name: 'email', type: 'string' },
              { name: 'password', type: 'string' },
            ],
            output: 'User',
          },
        },
        ports: {
          UserRepository: {
            methods: [
              {
                name: 'save',
                parameters: { user: 'User' },
                returnType: 'User',
              },
            ],
          },
        },
        adapters: {
          PostgresUserRepository: {
            implements: 'UserRepository',
          },
        },
      },
    },
    iot: [
      {
        name: 'blink',
        protocol: 'gpio',
        driver: 'rppal',
        expose: {
          method: 'POST',
        },
      },
    ],
  };

  const dslValidation = validateFerrumDSL(validDSL);
  assert(dslValidation.valid, 'Valid DSL should pass validation');
  assert(isFerrumDSL(validDSL), 'Type guard should identify valid DSL');
  console.log('✅ Valid DSL validation passed\n');

  // Test 4: Invalid FerrumDSL
  console.log('Test 4: Invalid FerrumDSL validation');
  const invalidDSL = {
    app: {
      // missing required name field
    },
  };

  const invalidDslValidation = validateFerrumDSL(invalidDSL);
  assert(!invalidDslValidation.valid, 'Invalid DSL should fail validation');
  assert(!isFerrumDSL(invalidDSL), 'Type guard should reject invalid DSL');
  assert(invalidDslValidation.errors && invalidDslValidation.errors.length > 0, 'Should have validation errors');
  console.log('✅ Invalid DSL validation passed\n');

  // Test 5: Serialization/Deserialization
  console.log('Test 5: Serialization/Deserialization');
  
  const serializedGraph = serializeFerrumGraphData(validGraphData);
  assert(typeof serializedGraph === 'string', 'Serialized graph should be a string');
  
  const deserializedGraph = deserializeFerrumGraphData(serializedGraph);
  assert(JSON.stringify(deserializedGraph) === JSON.stringify(validGraphData), 'Deserialized graph should match original');
  
  const serializedDSL = serializeFerrumDSL(validDSL);
  assert(typeof serializedDSL === 'string', 'Serialized DSL should be a string');
  
  const deserializedDSL = deserializeFerrumDSL(serializedDSL);
  assert(JSON.stringify(deserializedDSL) === JSON.stringify(validDSL), 'Deserialized DSL should match original');
  console.log('✅ Serialization/Deserialization passed\n');

  // Test 6: Node Types
  console.log('Test 6: Node Types');
  const nodeTypes = ['module', 'usecase', 'adapter', 'port', 'entity', 'event', 'handler', 'service', 'iot'];
  
  nodeTypes.forEach(type => {
    const graphData: FerrumGraphData = {
      framework: 'ferrum',
      version: '1.0.0',
      nodes: [
        {
          id: 'test-node',
          type: type as any,
          position: { x: 0, y: 0 },
          data: {},
        },
      ],
      edges: [],
      metadata: {
        module: 'test',
        created_at: '2025-01-10T00:00:00Z',
        last_modified: '2025-01-10T00:00:00Z',
      },
    };

    const result = validateFerrumGraphData(graphData);
    assert(result.valid, `Node type ${type} should be valid`);
  });
  console.log('✅ All node types validation passed\n');

  // Test 7: Edge Types
  console.log('Test 7: Edge Types');
  const edgeTypes = ['dependency', 'implementation', 'data_flow', 'calls', 'extends', 'aggregates'];
  
  edgeTypes.forEach(type => {
    const graphData: FerrumGraphData = {
      framework: 'ferrum',
      version: '1.0.0',
      nodes: [
        {
          id: 'node1',
          type: 'module',
          position: { x: 0, y: 0 },
          data: {},
        },
        {
          id: 'node2',
          type: 'usecase',
          position: { x: 100, y: 100 },
          data: {},
        },
      ],
      edges: [
        {
          id: 'test-edge',
          source: 'node1',
          target: 'node2',
          type: type as any,
        },
      ],
      metadata: {
        module: 'test',
        created_at: '2025-01-10T00:00:00Z',
        last_modified: '2025-01-10T00:00:00Z',
      },
    };

    const result = validateFerrumGraphData(graphData);
    assert(result.valid, `Edge type ${type} should be valid`);
  });
  console.log('✅ All edge types validation passed\n');

  console.log('🎉 All tests passed! Ferrum types are working correctly.');
}

// Run the tests
try {
  runTests();
} catch (error) {
  console.error('❌ Test failed:', error);
  process.exit(1);
}