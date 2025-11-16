/**
 * Ferrum Types Test Suite
 * 
 * Tests for Ferrum framework type definitions, validation schemas,
 * and serialization/deserialization functions.
 */

// Remove jest imports for now since jest config is broken
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
} from '../shared/types/ferrum-types';

// Simple test runner for Ferrum types
function runTests() {
  console.log('Running Ferrum Types Tests...');
  
  // Test FerrumGraphData
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

    it('should validate valid graph data', () => {
      const result = validateFerrumGraphData(validGraphData);
      expect(result.valid).toBe(true);
      expect(result.errors).toBeUndefined();
    });

    it('should reject invalid graph data', () => {
      const invalidData = {
        framework: 'invalid',
        version: '1.0.0',
        nodes: [],
        edges: [],
        metadata: {},
      };

      const result = validateFerrumGraphData(invalidData);
      expect(result.valid).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.length).toBeGreaterThan(0);
    });

    it('should serialize and deserialize graph data', () => {
      const serialized = serializeFerrumGraphData(validGraphData);
      expect(typeof serialized).toBe('string');

      const deserialized = deserializeFerrumGraphData(serialized);
      expect(deserialized).toEqual(validGraphData);
    });

    it('should identify valid graph data with type guard', () => {
      expect(isFerrumGraphData(validGraphData)).toBe(true);
      expect(isFerrumGraphData({ invalid: 'data' })).toBe(false);
    });
  });

  describe('FerrumDSL', () => {
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

    it('should validate valid DSL', () => {
      const result = validateFerrumDSL(validDSL);
      expect(result.valid).toBe(true);
      expect(result.errors).toBeUndefined();
    });

    it('should reject invalid DSL', () => {
      const invalidDSL = {
        app: {
          // missing required name field
        },
      };

      const result = validateFerrumDSL(invalidDSL);
      expect(result.valid).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors!.length).toBeGreaterThan(0);
    });

    it('should serialize and deserialize DSL', () => {
      const serialized = serializeFerrumDSL(validDSL);
      expect(typeof serialized).toBe('string');

      const deserialized = deserializeFerrumDSL(serialized);
      expect(deserialized).toEqual(validDSL);
    });

    it('should identify valid DSL with type guard', () => {
      expect(isFerrumDSL(validDSL)).toBe(true);
      expect(isFerrumDSL({ invalid: 'data' })).toBe(false);
    });
  });

  describe('Node Types', () => {
    it('should support all expected node types', () => {
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
        expect(result.valid).toBe(true);
      });
    });
  });

  describe('Edge Types', () => {
    it('should support all expected edge types', () => {
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
        expect(result.valid).toBe(true);
      });
    });
  });
});