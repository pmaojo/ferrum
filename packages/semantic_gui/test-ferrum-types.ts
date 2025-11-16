// Simple test to verify Ferrum types compile correctly
import {
  FerrumGraphData,
  FerrumDSL,
  validateFerrumGraphData,
  validateFerrumDSL,
} from './shared/types/ferrum-types';

// Test data
const testGraphData: FerrumGraphData = {
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
  ],
  edges: [],
  metadata: {
    module: 'test-module',
    created_at: '2025-01-10T00:00:00Z',
    last_modified: '2025-01-10T00:00:00Z',
  },
};

const testDSL: FerrumDSL = {
  app: {
    name: 'TestApp',
    features: ['auth'],
  },
  modules: {
    users: {
      entity: {
        fields: {
          email: 'string',
          password: 'string',
        },
      },
    },
  },
};

// Test validation
const graphValidation = validateFerrumGraphData(testGraphData);
const dslValidation = validateFerrumDSL(testDSL);

console.log('Graph validation:', graphValidation.valid);
console.log('DSL validation:', dslValidation.valid);