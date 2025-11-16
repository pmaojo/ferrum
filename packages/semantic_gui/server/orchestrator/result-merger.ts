import type { InsertGraphNode, InsertGraphEdge } from '@shared/schema';

import type { AnalysisResult, IArchitecturalPattern } from './types';

/**
 * Merges the results of multiple analyzers, removing duplicates.
 */
export function mergeAnalysisResults(
  results: AnalysisResult[]
): AnalysisResult {
  const merged: AnalysisResult = {
    nodes: [],
    edges: [],
    patterns: [],
    validationResults: [],
    businessRules: [],
    suggestions: [],
  };

  const nodeMap = new Map<string, InsertGraphNode>();
  const edgeMap = new Map<string, InsertGraphEdge>();
  const patternMap = new Map<string, IArchitecturalPattern>();

  results.forEach((result, index) => {
    result.nodes.forEach(node => {
      const key = `${node.name}-${node.type}`;
      if (!nodeMap.has(key) || index > 0) {
        nodeMap.set(key, node);
      }
    });

    result.edges.forEach(edge => {
      const key = `${edge.sourceNodeId}-${edge.targetNodeId}-${edge.type}`;
      if (!edgeMap.has(key)) {
        edgeMap.set(key, edge);
      }
    });

    result.patterns.forEach(pattern => {
      if (!patternMap.has(pattern.id)) {
        patternMap.set(pattern.id, pattern);
      }
    });

    merged.validationResults.push(...result.validationResults);
    merged.businessRules?.push(...(result.businessRules || []));
    merged.suggestions?.push(...(result.suggestions || []));
  });

  merged.nodes = Array.from(nodeMap.values());
  merged.edges = Array.from(edgeMap.values());
  merged.patterns = Array.from(patternMap.values());

  return merged;
}

/**
 * Merges a new analysis result with existing graph data.
 */
export function mergeWithExisting(
  newResult: AnalysisResult,
  existingNodes: InsertGraphNode[],
  existingEdges: InsertGraphEdge[]
): AnalysisResult {
  const nodeMap = new Map(existingNodes.map(n => [n.id, n]));

  newResult.nodes.forEach(newNode => {
    const existing = Array.from(nodeMap.values()).find(
      n => n.name === newNode.name && n.type === newNode.type
    );

    if (existing) {
      nodeMap.set(existing.id, { ...existing, ...newNode, id: existing.id });
    } else {
      nodeMap.set((newNode as any).id || `new_${Date.now()}`, newNode);
    }
  });

  return {
    ...newResult,
    nodes: Array.from(nodeMap.values()),
    edges: [...existingEdges, ...newResult.edges],
  };
}
