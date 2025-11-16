/**
 * GraphRagNode for Flowise AI canvas integration.
 *
 * This file implements a CustomNode for Flowise AI that exposes GraphRAG
 * functionality for knowledge graph querying and document processing.
 *
 * Requirements:
 * - 10.1: Implement GraphRagNode with graphrag.query() exposure
 * - 3.1: Integrate with Flowise AI framework
 */

const { INode, INodeData, INodeParams } = require('flowise-components')

/**
 * GraphRagNode class for Flowise AI integration.
 *
 * Exposes GraphRAG functionality as a custom node in the Flowise canvas,
 * allowing users to query knowledge graphs using natural language.
 */
class GraphRagNode {
    constructor() {
        this.label = 'GraphRAG'
        this.name = 'graphRagNode'
        this.type = 'GraphRAG'
        this.icon = 'graphrag.svg'
        this.category = 'Knowledge Graphs'
        this.description = 'Query ontology-validated knowledge graphs using natural language'
        this.baseClasses = ['GraphRAG', 'Tool', 'GraphRetriever']
        this.inputs = [
            {
                label: 'API Endpoint',
                name: 'apiEndpoint',
                type: 'string',
                default: 'http://localhost:8000/api/graphrag',
                placeholder: 'http://localhost:8000/api/graphrag',
                description: 'GraphRAG API endpoint URL',
            },
            {
                label: 'API Key',
                name: 'apiKey',
                type: 'password',
                optional: true,
                description: 'API key for authentication (if required)',
            },
            {
                label: 'Knowledge Graph ID',
                name: 'kgId',
                type: 'string',
                default: 'default',
                description: 'Knowledge graph identifier',
            },
            {
                label: 'Tenant ID',
                name: 'tenantId',
                type: 'string',
                default: 'default',
                description: 'Tenant identifier for multi-tenant isolation',
            },
            {
                label: 'Max Hops',
                name: 'maxHops',
                type: 'number',
                default: 2,
                optional: true,
                description: 'Maximum graph traversal depth',
            },
            {
                label: 'Context Tokens',
                name: 'contextTokens',
                type: 'number',
                default: 4096,
                optional: true,
                description: 'Maximum context window size',
            },
            {
                label: 'Return Format',
                name: 'returnFormat',
                type: 'options',
                options: [
                    {
                        label: 'Text',
                        name: 'text',
                    },
                    {
                        label: 'Triples',
                        name: 'triples',
                    },
                    {
                        label: 'JSON',
                        name: 'json',
                    },
                ],
                default: 'text',
                description: 'Format for query results',
            },
            {
                label: 'Include Reasoning',
                name: 'includeReasoning',
                type: 'boolean',
                default: true,
                optional: true,
                description: 'Include reasoning steps in query results',
            },
            {
                label: 'Ontology Version ID',
                name: 'ontologyVersionId',
                type: 'string',
                default: 'latest',
                optional: true,
                description: 'Ontology version for validation',
            },
            {
                label: 'Input Variable',
                name: 'inputVariable',
                type: 'string',
                default: 'question',
                description: 'Input variable name for dynamic inputs',
            },
        ]
        this.outputs = [
            {
                label: 'GraphRAG',
                name: 'graphrag',
                baseClasses: ['GraphRAG', 'Tool', 'GraphRetriever'],
            },
            {
                label: 'String Output',
                name: 'string',
                baseClasses: ['string', 'json'],
            },
        ]
    }

    /**
     * Build the GraphRAG node for Flowise canvas.
     *
     * @param {INodeData} data - Node configuration data
     * @returns {Promise<object>} - GraphRAG node instance
     */
    async build(data) {
        const apiEndpoint = data.apiEndpoint
        const apiKey = data.apiKey
        const kgId = data.kgId
        const tenantId = data.tenantId
        const maxHops = data.maxHops || 2
        const contextTokens = data.contextTokens || 4096
        const returnFormat = data.returnFormat || 'text'
        const includeReasoning = data.includeReasoning !== false
        const ontologyVersionId = data.ontologyVersionId || 'latest'
        const inputVariable = data.inputVariable || 'question'

        // Validate required parameters
        if (!apiEndpoint) {
            throw new Error('API endpoint is required')
        }

        // Create GraphRAG client
        const graphRagClient = {
            /**
             * Query the knowledge graph using natural language.
             *
             * @param {string} question - Natural language query
             * @param {object} options - Additional query options
             * @returns {Promise<object>} - Query results
             */
            query: async (question, options = {}) => {
                try {
                    // Prepare request options
                    const requestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            question,
                            kg_id: options.kgId || kgId,
                            tenant_id: options.tenantId || tenantId,
                            opts: {
                                max_hops: options.maxHops || maxHops,
                                context_tokens: options.contextTokens || contextTokens,
                                return_triples: returnFormat === 'triples',
                                return_json: returnFormat === 'json',
                                include_reasoning:
                                    options.includeReasoning !== undefined
                                        ? options.includeReasoning
                                        : includeReasoning,
                            },
                        }),
                    }

                    // Execute API request
                    const response = await fetch(`${apiEndpoint}/query`, requestOptions)

                    if (!response.ok) {
                        const errorText = await response.text()
                        throw new Error(`GraphRAG API error (${response.status}): ${errorText}`)
                    }

                    // Parse and return results
                    const result = await response.json()
                    return result
                } catch (error) {
                    console.error('GraphRAG query error:', error)
                    throw new Error(`GraphRAG query failed: ${error.message}`)
                }
            },

            /**
             * Index documents into the knowledge graph.
             *
             * @param {Array<string>} docs - Document content strings
             * @param {object} options - Additional indexing options
             * @returns {Promise<object>} - Indexing results
             */
            index: async (docs, options = {}) => {
                try {
                    // Prepare request options
                    const requestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            docs,
                            kg_id: options.kgId || kgId,
                            tenant_id: options.tenantId || tenantId,
                            validate: options.validate !== false,
                            ontology_version_id: options.ontologyVersionId || ontologyVersionId,
                        }),
                    }

                    // Execute API request
                    const response = await fetch(`${apiEndpoint}/index`, requestOptions)

                    if (!response.ok) {
                        const errorText = await response.text()
                        throw new Error(`GraphRAG API error (${response.status}): ${errorText}`)
                    }

                    // Parse and return results
                    const result = await response.json()
                    return result
                } catch (error) {
                    console.error('GraphRAG indexing error:', error)
                    throw new Error(`GraphRAG indexing failed: ${error.message}`)
                }
            },

            /**
             * Create and execute a workflow.
             *
             * @param {string} workflowId - Workflow identifier
             * @param {Array<object>} steps - Workflow steps
             * @param {object} inputData - Input data for workflow execution
             * @param {object} options - Additional workflow options
             * @returns {Promise<object>} - Workflow execution results
             */
            executeWorkflow: async (workflowId, steps, inputData, options = {}) => {
                try {
                    // First create the workflow if steps are provided
                    if (steps && steps.length > 0) {
                        const createRequestOptions = {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                            },
                            body: JSON.stringify({
                                workflow_id: workflowId,
                                steps,
                                tenant_id: options.tenantId || tenantId,
                            }),
                        }

                        const createResponse = await fetch(
                            `${apiEndpoint}/workflow/create`,
                            createRequestOptions
                        )

                        if (!createResponse.ok) {
                            const errorText = await createResponse.text()
                            throw new Error(
                                `Workflow creation failed (${createResponse.status}): ${errorText}`
                            )
                        }
                    }

                    // Execute the workflow
                    const executeRequestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            workflow_id: workflowId,
                            input_data: inputData,
                            tenant_id: options.tenantId || tenantId,
                        }),
                    }

                    const executeResponse = await fetch(
                        `${apiEndpoint}/workflow/execute`,
                        executeRequestOptions
                    )

                    if (!executeResponse.ok) {
                        const errorText = await executeResponse.text()
                        throw new Error(
                            `Workflow execution failed (${executeResponse.status}): ${errorText}`
                        )
                    }

                    // Parse and return results
                    const result = await executeResponse.json()
                    return result
                } catch (error) {
                    console.error('Workflow execution error:', error)
                    throw new Error(`Workflow execution failed: ${error.message}`)
                }
            },

            /**
             * Tool interface for LLM integration.
             */
            name: 'graphrag',
            description: 'Query ontology-validated knowledge graphs using natural language',
            schema: {
                type: 'function',
                function: {
                    name: 'graphrag',
                    description: 'Query ontology-validated knowledge graphs using natural language',
                    parameters: {
                        type: 'object',
                        properties: {
                            question: {
                                type: 'string',
                                description: 'Natural language query to the knowledge graph',
                            },
                            kg_id: {
                                type: 'string',
                                description: 'Knowledge graph identifier',
                                default: kgId,
                            },
                            max_hops: {
                                type: 'number',
                                description: 'Maximum graph traversal depth',
                                default: maxHops,
                            },
                        },
                        required: ['question'],
                    },
                },
            },

            /**
             * Execute the tool with parameters.
             *
             * @param {object} parameters - Tool parameters
             * @returns {Promise<string>} - Tool execution result
             */
            invoke: async (parameters) => {
                const result = await graphRagClient.query(parameters.question, {
                    kgId: parameters.kg_id,
                    maxHops: parameters.max_hops,
                })

                if (typeof result === 'string') {
                    return result
                } else if (result.results && Array.isArray(result.results)) {
                    return result.results.join('\n')
                } else {
                    return JSON.stringify(result)
                }
            },

            /**
             * Execute a workflow with fallback mechanism.
             *
             * @param {string} workflowId - Primary workflow identifier
             * @param {object} inputData - Input data for workflow execution
             * @param {string} fallbackWorkflowId - Fallback workflow identifier
             * @param {object} options - Additional options
             * @returns {Promise<object>} - Workflow execution results
             */
            executeWithFallback: async (
                workflowId,
                inputData,
                fallbackWorkflowId,
                options = {}
            ) => {
                try {
                    // Prepare request options
                    const requestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            workflow_id: workflowId,
                            input_data: inputData,
                            fallback_workflow_id: fallbackWorkflowId,
                            tenant_id: options.tenantId || tenantId,
                            max_retries: options.maxRetries || 3,
                            retry_delay_seconds: options.retryDelaySeconds || 2,
                        }),
                    }

                    // Execute API request
                    const response = await fetch(
                        `${apiEndpoint}/workflow/execute-with-fallback`,
                        requestOptions
                    )

                    if (!response.ok) {
                        const errorText = await response.text()
                        throw new Error(
                            `Workflow execution failed (${response.status}): ${errorText}`
                        )
                    }

                    // Parse and return results
                    const result = await response.json()
                    return result
                } catch (error) {
                    console.error('Workflow execution error:', error)
                    throw new Error(`Workflow execution failed: ${error.message}`)
                }
            },

            /**
             * Execute multiple workflows in parallel.
             *
             * @param {Array<object>} workflowConfigs - Workflow configurations
             * @param {object} options - Additional options
             * @returns {Promise<object>} - Aggregated workflow execution results
             */
            executeParallelWorkflows: async (workflowConfigs, options = {}) => {
                try {
                    // Prepare request options
                    const requestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            workflow_configs: workflowConfigs,
                            tenant_id: options.tenantId || tenantId,
                            timeout_seconds: options.timeoutSeconds || 60,
                            aggregate_results: options.aggregateResults !== false,
                        }),
                    }

                    // Execute API request
                    const response = await fetch(
                        `${apiEndpoint}/workflow/execute-parallel`,
                        requestOptions
                    )

                    if (!response.ok) {
                        const errorText = await response.text()
                        throw new Error(
                            `Parallel workflow execution failed (${response.status}): ${errorText}`
                        )
                    }

                    // Parse and return results
                    const result = await response.json()
                    return result
                } catch (error) {
                    console.error('Parallel workflow execution error:', error)
                    throw new Error(`Parallel workflow execution failed: ${error.message}`)
                }
            },

            /**
             * Register a workflow template.
             *
             * @param {string} templateId - Template identifier
             * @param {string} name - Template name
             * @param {string} description - Template description
             * @param {Array<object>} steps - Workflow steps
             * @param {object} inputSchema - Input schema
             * @param {object} outputSchema - Output schema
             * @param {object} options - Additional options
             * @returns {Promise<object>} - Template registration result
             */
            registerWorkflowTemplate: async (
                templateId,
                name,
                description,
                steps,
                inputSchema,
                outputSchema,
                options = {}
            ) => {
                try {
                    // Prepare request options
                    const requestOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            ...(apiKey && { Authorization: `Bearer ${apiKey}` }),
                        },
                        body: JSON.stringify({
                            template_id: templateId,
                            name,
                            description,
                            steps,
                            input_schema: inputSchema,
                            output_schema: outputSchema,
                            tenant_id: options.tenantId || tenantId,
                        }),
                    }

                    // Execute API request
                    const response = await fetch(`${apiEndpoint}/workflow/template`, requestOptions)

                    if (!response.ok) {
                        const errorText = await response.text()
                        throw new Error(
                            `Template registration failed (${response.status}): ${errorText}`
                        )
                    }

                    // Parse and return results
                    const result = await response.json()
                    return result
                } catch (error) {
                    console.error('Template registration error:', error)
                    throw new Error(`Template registration failed: ${error.message}`)
                }
            },
        }

        return graphRagClient
    }

    /**
     * Execute the GraphRAG node with input data.
     *
     * @param {INodeData} nodeData - Node configuration data
     * @param {object} inputs - Node input data
     * @returns {Promise<object>} - Node execution results
     */
    async run(nodeData, inputs) {
        const graphRagClient = nodeData.instance
        const inputVariable = nodeData.data?.inputVariable || 'question'

        // Get input from the specified variable
        const question = inputs[inputVariable]

        // Validate inputs
        if (!question) {
            throw new Error(`Input variable '${inputVariable}' is required but not provided`)
        }

        if (!graphRagClient) {
            throw new Error('GraphRAG client not initialized')
        }

        try {
            // Execute query
            const result = await graphRagClient.query(question)

            // Return both the client and the result for different output types
            return { graphrag: graphRagClient, string: this.formatOutput(result) }
        } catch (error) {
            console.error('GraphRAG execution error:', error)

            // Return error with fallback mechanism
            const errorMessage = `GraphRAG execution failed: ${error.message}`
            return {
                graphrag: graphRagClient,
                string: JSON.stringify({
                    error: errorMessage,
                    fallback: 'Unable to retrieve information from the knowledge graph.',
                }),
            }
        }
    }

    /**
     * Format the output based on the result type.
     *
     * @param {any} result - Query result
     * @returns {string} - Formatted output
     */
    formatOutput(result) {
        if (typeof result === 'string') {
            return result
        } else if (result.results && Array.isArray(result.results)) {
            return result.results.join('\n')
        } else {
            return JSON.stringify(result)
        }
    }
}

module.exports = { nodeClass: GraphRagNode }
