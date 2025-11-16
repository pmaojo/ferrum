/**
 * Gemini-GraphRAG node for Flowise AI framework.
 *
 * This node integrates Google's Gemini LLM with GraphRAG for knowledge graph
 * querying and document indexing with configurable parameters.
 *
 * Requirements:
 * - 10.1: Create CustomNode for Flowise canvas integration
 * - 10.2: Add visual configuration for temperature, top_p, context_tokens
 *
 * Features:
 * - Seamless integration with Google's Gemini 2.5 flash LLM
 * - Configurable parameters for fine-tuning generation quality
 * - Support for both querying and indexing operations
 * - Multi-tenant isolation with tenant_id parameter
 * - Safety settings configuration for content filtering
 * - Ontology validation for knowledge graph consistency
 *
 * Example Usage:
 * ```javascript
 * // Query mode example
 * const result = await geminiGraphRAG.execute({
 *   question: "What is the relationship between Alice and Bob?",
 *   kg_id: "my_knowledge_graph",
 *   temperature: 0.5,
 *   context_tokens: 2048
 * });
 *
 * // Index mode example
 * const result = await geminiGraphRAG.execute({
 *   docs: ["Alice is Bob's sister.", "Bob works at Acme Corp."],
 *   kg_id: "my_knowledge_graph",
 *   validate_ontology: true
 * });
 *
 * // Advanced configuration example
 * const result = await geminiGraphRAG.execute({
 *   question: "What projects is Bob working on at Acme Corp?",
 *   kg_id: "my_knowledge_graph",
 *   tenant_id: "customer-123",
 *   temperature: 0.3,
 *   top_p: 0.92,
 *   context_tokens: 6144,
 *   max_hops: 3,
 *   safety_settings: "high"
 * });
 * ```
 */

const { ICommonObject, INode, INodeData, INodeParams } = require('flowise-components')

/**
 * Gemini-GraphRAG node for Flowise AI framework.
 */
class GeminiGraphRAGNode {
    /**
     * Node configuration for Flowise canvas.
     */
    constructor() {
        this.label = 'Gemini GraphRAG'
        this.name = 'geminiGraphRAG'
        this.version = 1.0
        this.type = 'GeminiGraphRAG'
        this.icon = 'gemini.svg'
        this.category = 'Knowledge Graphs'
        this.description = 'Query knowledge graphs using Google Gemini LLM with GraphRAG'
        this.baseClasses = ['GeminiGraphRAG']
        this.inputs = [
            {
                label: 'Mode',
                name: 'mode',
                type: 'options',
                options: [
                    {
                        label: 'Query',
                        name: 'query',
                    },
                    {
                        label: 'Index',
                        name: 'index',
                    },
                ],
                default: 'query',
                description: 'Operation mode: query knowledge graph or index documents',
            },
            {
                label: 'Knowledge Graph ID',
                name: 'kgId',
                type: 'string',
                default: 'default',
                description: 'Identifier for the knowledge graph',
            },
            {
                label: 'Tenant ID',
                name: 'tenantId',
                type: 'string',
                default: 'default',
                description: 'Tenant identifier for multi-tenant isolation',
            },
            {
                label: 'Temperature',
                name: 'temperature',
                type: 'number',
                default: 0.7,
                description: 'Sampling temperature (0.0 to 1.0) - lower is more deterministic',
            },
            {
                label: 'Top P',
                name: 'topP',
                type: 'number',
                default: 0.95,
                description: 'Nucleus sampling parameter (0.0 to 1.0)',
            },
            {
                label: 'Context Tokens',
                name: 'contextTokens',
                type: 'number',
                default: 4096,
                description: 'Maximum context tokens for query processing',
            },
            {
                label: 'Max Hops',
                name: 'maxHops',
                type: 'number',
                default: 2,
                description: 'Maximum graph traversal hops for query processing',
            },
            {
                label: 'Safety Settings',
                name: 'safetySettings',
                type: 'options',
                options: [
                    {
                        label: 'Standard',
                        name: 'standard',
                    },
                    {
                        label: 'High',
                        name: 'high',
                    },
                    {
                        label: 'Maximum',
                        name: 'maximum',
                    },
                    {
                        label: 'None',
                        name: 'none',
                    },
                ],
                default: 'standard',
                description: 'Safety filter level for Gemini LLM',
            },
            {
                label: 'Validate Ontology',
                name: 'validateOntology',
                type: 'boolean',
                default: true,
                description:
                    'Whether to validate extracted triples against ontology (for indexing)',
            },
            {
                label: 'Ontology Version ID',
                name: 'ontologyVersionId',
                type: 'string',
                default: 'latest',
                description: 'Ontology version for validation (for indexing)',
            },
        ]
    }

    /**
     * Build node for execution.
     * @param {INodeData} data - Node configuration data
     * @param {ICommonObject} inputs - Node inputs
     * @returns {Promise<any>} - Node execution result
     */
    async init(data, inputs) {
        // Extract configuration
        const mode = data.mode || 'query'
        const kgId = data.kgId || 'default'
        const tenantId = data.tenantId || 'default'
        const temperature = parseFloat(data.temperature || 0.7)
        const topP = parseFloat(data.topP || 0.95)
        const contextTokens = parseInt(data.contextTokens || 4096)
        const maxHops = parseInt(data.maxHops || 2)
        const safetySettings = data.safetySettings || 'standard'
        const validateOntology = data.validateOntology !== false
        const ontologyVersionId = data.ontologyVersionId || 'latest'

        // Map safety settings to Gemini format
        const safetySettingsMap = {
            standard: {
                HARM_CATEGORY_HARASSMENT: 'BLOCK_MEDIUM_AND_ABOVE',
                HARM_CATEGORY_HATE_SPEECH: 'BLOCK_MEDIUM_AND_ABOVE',
                HARM_CATEGORY_SEXUALLY_EXPLICIT: 'BLOCK_MEDIUM_AND_ABOVE',
                HARM_CATEGORY_DANGEROUS_CONTENT: 'BLOCK_MEDIUM_AND_ABOVE',
            },
            high: {
                HARM_CATEGORY_HARASSMENT: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_HATE_SPEECH: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_SEXUALLY_EXPLICIT: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_DANGEROUS_CONTENT: 'BLOCK_LOW_AND_ABOVE',
            },
            maximum: {
                HARM_CATEGORY_HARASSMENT: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_HATE_SPEECH: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_SEXUALLY_EXPLICIT: 'BLOCK_LOW_AND_ABOVE',
                HARM_CATEGORY_DANGEROUS_CONTENT: 'BLOCK_LOW_AND_ABOVE',
            },
            none: {
                HARM_CATEGORY_HARASSMENT: 'BLOCK_NONE',
                HARM_CATEGORY_HATE_SPEECH: 'BLOCK_NONE',
                HARM_CATEGORY_SEXUALLY_EXPLICIT: 'BLOCK_NONE',
                HARM_CATEGORY_DANGEROUS_CONTENT: 'BLOCK_NONE',
            },
        }

        // Create options object
        const opts = {
            temperature,
            top_p: topP,
            context_tokens: contextTokens,
            max_hops: maxHops,
            safety_settings: safetySettingsMap[safetySettings] || safetySettingsMap.standard,
            llm_provider: 'gemini',
        }

        // Return node implementation
        return {
            /**
             * Execute node with input data.
             * @param {ICommonObject} input - Input data
             * @returns {Promise<any>} - Execution result
             *
             * Return Value Format:
             *
             * Query mode return value:
             * ```javascript
             * {
             *   "results": [
             *     {"subject": "Bob", "predicate": "works_on", "object": "Project X"},
             *     {"subject": "Project X", "predicate": "part_of", "object": "Acme Corp"}
             *   ],
             *   "explanation": "Bob is working on Project X at Acme Corp...",
             *   "metadata": {
             *     "query_time_ms": 245,
             *     "node_count": 15,
             *     "edge_count": 23
             *   }
             * }
             * ```
             *
             * Index mode return value:
             * ```javascript
             * {
             *   "status": "success",
             *   "triple_count": 5,
             *   "kg_id": "my_knowledge_graph",
             *   "tenant_id": "customer-123",
             *   "validation": {
             *     "performed": true,
             *     "is_consistent": true
             *   }
             * }
             * ```
             */
            async execute(input) {
                try {
                    // Get Python adapter instance
                    const { graphragAdapter } = global

                    if (!graphragAdapter) {
                        throw new Error(
                            'GraphRAG adapter not found. Make sure the adapter is properly initialized.'
                        )
                    }

                    // Process based on mode
                    if (mode === 'query') {
                        // Extract question from input
                        const question = input.question || input.input || input.text

                        if (!question) {
                            throw new Error('No question provided for query mode')
                        }

                        console.log(
                            `Executing Gemini GraphRAG query: "${question.substring(0, 50)}..." with parameters:`,
                            {
                                kg_id: kgId,
                                tenant_id: tenantId,
                                temperature: opts.temperature,
                                top_p: opts.top_p,
                                context_tokens: opts.context_tokens,
                                max_hops: opts.max_hops,
                            }
                        )

                        // Execute query
                        const result = await graphragAdapter.query_knowledge_graph({
                            question,
                            kg_id: kgId,
                            tenant_id: tenantId,
                            opts,
                        })

                        return result
                    } else if (mode === 'index') {
                        // Extract documents from input
                        const docs = input.docs || input.documents || input.texts || []

                        if (!docs || docs.length === 0) {
                            throw new Error('No documents provided for index mode')
                        }

                        console.log(
                            `Executing Gemini GraphRAG indexing: ${docs.length} documents with parameters:`,
                            {
                                kg_id: kgId,
                                tenant_id: tenantId,
                                validate_ontology: validateOntology,
                                ontology_version_id: ontologyVersionId,
                            }
                        )

                        // Execute indexing
                        const result = await graphragAdapter.index_documents({
                            docs,
                            kg_id: kgId,
                            tenant_id: tenantId,
                            validate: validateOntology,
                            ontology_version_id: ontologyVersionId,
                        })

                        return result
                    } else {
                        throw new Error(`Invalid mode: ${mode}`)
                    }
                } catch (error) {
                    console.error('Gemini GraphRAG node execution error:', error)

                    // Return a more user-friendly error response
                    return {
                        error: error.message,
                        status: 'failed',
                        suggestions: [
                            'Check that the GraphRAG adapter is properly initialized',
                            'Verify that your input parameters are correct',
                            'Ensure that the knowledge graph exists',
                            'Check that the Gemini API key is valid and has sufficient quota',
                        ],
                    }
                }
            },
        }
    }
}

module.exports = { nodeClass: GeminiGraphRAGNode }
