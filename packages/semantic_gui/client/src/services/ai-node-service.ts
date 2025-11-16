import type { InsertGraphNode } from '@shared/schema';

export interface AINodeSuggestion {
  name: string;
  type: string;
  description?: string;
  metadata?: Record<string, any>;
  position: { x: number; y: number };
}

/**
 * Requests the backend AI service to generate nodes for a given message.
 */
export async function requestAINodes(
  message: string
): Promise<AINodeSuggestion[]> {
  const response = await fetch('/api/v1/ai/nodes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error('AI node generation failed');
  }

  return (await response.json()) as AINodeSuggestion[];
}

/**
 * Generates nodes via AI and persists them using the provided create function.
 */
export async function createNodesFromAI(
  message: string,
  projectId: string,
  templateId: string,
  createNode: (data: InsertGraphNode) => Promise<any>
) {
  const suggestions = await requestAINodes(message);
  const results = [];

  for (const suggestion of suggestions) {
    const nodeData: InsertGraphNode = {
      name: suggestion.name,
      type: suggestion.type,
      description: suggestion.description || '',
      metadata: { ...suggestion.metadata, aiGenerated: true },
      projectId,
      templateId,
      position: suggestion.position,
    };

    const created = await createNode(nodeData);
    results.push({ ...created, position: suggestion.position });
  }

  return results;
}
