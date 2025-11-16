/**
 * Tests for GraphRagNode Flowise integration.
 * 
 * This file contains tests for the GraphRagNode implementation,
 * verifying proper integration with the Flowise canvas.
 */

const { nodeClass: GraphRagNode } = require('../ui_adapters/flowise/graphrag_node')
const assert = require('assert')

// Mock fetch for testing
global.fetch = jest.fn()

describe('GraphRagNode', () => {
    let graphRagNode
    
    beforeEach(() => {
        // Reset fetch mock
        global.fetch.mockReset()
        
        // Create node instance
        graphRagNode = new GraphRagNode()
    })
    
    test('should have correct node properties', () => {
        // Verify node metadata
        expect(graphRagNode.label).toBe('GraphRAG')
        expect(graphRagNode.name).toBe('graphRagNode')
        expect(graphRagNode.type).toBe('GraphRAG')
        expect(graphRagNode.category).toBe('Knowledge Graphs')
        expect(graphRagNode.baseClasses).toContain('GraphRAG')
        expect(graphRagNode.baseClasses).toContain('Tool')
        expect(graphRagNode.baseClasses).toContain('GraphRetriever')
    })
    
    test('should have required input parameters', () => {
        // Verify input parameters
        const inputNames = graphRagNode.inputs.map(input => input.name)
        expect(inputNames).toContain('apiEndpoint')
        expect(inputNames).toContain('apiKey')
        expect(inputNames).toContain('kgId')
        expect(inputNames).toContain('tenantId')
        expect(inputNames).toContain('maxHops')
        expect(inputNames).toContain('contextTokens')
        expect(inputNames).toContain('returnFormat')
        expect(inputNames).toContain('includeReasoning')
        expect(inputNames).toContain('ontologyVersionId')
        expect(inputNames).toContain('inputVariable')
    })
    
    test('should have defined outputs', () => {
        // Verify output definitions
        const outputNames = graphRagNode.outputs.map(output => output.name)
        expect(outputNames).toContain('graphrag')
        expect(outputNames).toContain('string')
    })
    
    test('should build GraphRAG client with correct configuration', async () => {
        // Configure node data
        const nodeData = {
            apiEndpoint: 'http://test-api.com/graphrag',
            apiKey: 'test-api-key',
            kgId: 'test-kg',
            tenantId: 'test-tenant',
            maxHops: 3,
            contextTokens: 2048,
            returnFormat: 'json',
            includeReasoning: true,
            ontologyVersionId: 'v1',
            inputVariable: 'input'
        }
        
        // Build client
        const client = await graphRagNode.build(nodeData)
        
        // Verify client properties
        expect(client.query).toBeDefined()
        expect(client.index).toBeDefined()
        expect(client.executeWorkflow).toBeDefined()
        expect(client.name).toBe('graphrag')
        expect(client.description).toBeDefined()
        expect(client.schema).toBeDefined()
        expect(client.invoke).toBeDefined()
    })
    
    test('should execute query with correct parameters', async () => {
        // Mock successful response
        const mockResponse = {
            results: ['Test result 1', 'Test result 2'],
            explanation: 'Test explanation'
        }
        
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockResponse
        })
        
        // Configure node data
        const nodeData = {
            apiEndpoint: 'http://test-api.com/graphrag',
            apiKey: 'test-api-key',
            kgId: 'test-kg',
            tenantId: 'test-tenant'
        }
        
        // Build client
        const client = await graphRagNode.build(nodeData)
        
        // Execute query
        const result = await client.query('What is GraphRAG?')
        
        // Verify fetch was called with correct parameters
        expect(global.fetch).toHaveBeenCalledTimes(1)
        expect(global.fetch).toHaveBeenCalledWith(
            'http://test-api.com/graphrag/query',
            expect.objectContaining({
                method: 'POST',
                headers: expect.objectContaining({
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer test-api-key'
                }),
                body: expect.any(String)
            })
        )
        
        // Verify request body
        const requestBody = JSON.parse(global.fetch.mock.calls[0][1].body)
        expect(requestBody.question).toBe('What is GraphRAG?')
        expect(requestBody.kg_id).toBe('test-kg')
        expect(requestBody.tenant_id).toBe('test-tenant')
        
        // Verify result
        expect(result).toEqual(mockResponse)
    })
    
    test('should handle query errors gracefully', async () => {
        // Mock error response
        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 500,
            text: async () => 'Internal server error'
        })
        
        // Configure node data
        const nodeData = {
            apiEndpoint: 'http://test-api.com/graphrag',
            kgId: 'test-kg'
        }
        
        // Build client
        const client = await graphRagNode.build(nodeData)
        
        // Execute query and expect error
        await expect(client.query('What is GraphRAG?')).rejects.toThrow('GraphRAG API error (500)')
    })
    
    test('should run node with input data', async () => {
        // Mock successful response
        const mockResponse = {
            results: ['Test result 1', 'Test result 2'],
            explanation: 'Test explanation'
        }
        
        // Mock client with query method
        const mockClient = {
            query: jest.fn().mockResolvedValue(mockResponse)
        }
        
        // Configure node data
        const nodeData = {
            instance: mockClient,
            data: {
                inputVariable: 'question'
            }
        }
        
        // Run node
        const result = await graphRagNode.run(nodeData, { question: 'What is GraphRAG?' })
        
        // Verify client query was called
        expect(mockClient.query).toHaveBeenCalledWith('What is GraphRAG?')
        
        // Verify result
        expect(result.graphrag).toBe(mockClient)
        expect(result.string).toBe('Test result 1\nTest result 2')
    })
    
    test('should handle run errors with fallback', async () => {
        // Mock client with query method that throws error
        const mockClient = {
            query: jest.fn().mockRejectedValue(new Error('Test error'))
        }
        
        // Configure node data
        const nodeData = {
            instance: mockClient,
            data: {
                inputVariable: 'question'
            }
        }
        
        // Run node
        const result = await graphRagNode.run(nodeData, { question: 'What is GraphRAG?' })
        
        // Verify client query was called
        expect(mockClient.query).toHaveBeenCalledWith('What is GraphRAG?')
        
        // Verify result contains error and fallback
        expect(result.graphrag).toBe(mockClient)
        expect(JSON.parse(result.string)).toHaveProperty('error')
        expect(JSON.parse(result.string)).toHaveProperty('fallback')
    })
    
    test('should format output correctly', () => {
        // Test string output
        expect(graphRagNode.formatOutput('Test string')).toBe('Test string')
        
        // Test array results
        expect(graphRagNode.formatOutput({ results: ['Result 1', 'Result 2'] })).toBe('Result 1\nResult 2')
        
        // Test object output
        const obj = { key: 'value' }
        expect(graphRagNode.formatOutput(obj)).toBe(JSON.stringify(obj))
    })
})