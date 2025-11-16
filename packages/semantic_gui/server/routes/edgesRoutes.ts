import type { Router } from 'express';

import type { IStorage } from '../storage';

export function attachEdgeRoutes(app: Router, storageImpl: IStorage) {
  app.post('/edges', async (req, res) => {
    try {
      const edgeData = req.body;
      if (
        !edgeData.sourceNodeId ||
        !edgeData.targetNodeId ||
        !edgeData.projectId
      ) {
        return res.status(400).json({
          error:
            'Missing required fields: sourceNodeId, targetNodeId, projectId',
        });
      }
      const validTypes = [
        'uses',
        'depends_on',
        'manages',
        'orchestrates',
        'transforms',
        'contains',
        'implements',
        'depends',
        'calls',
      ];
      const edgeType = edgeData.type || 'depends';
      if (!validTypes.includes(edgeType)) {
        return res.status(400).json({
          error: `Invalid edge type: ${edgeType}. Valid types: ${validTypes.join(', ')}`,
        });
      }
      const newEdge = await storageImpl.createGraphEdge({
        id: edgeData.id || `edge_${Date.now()}`,
        sourceNodeId: edgeData.sourceNodeId,
        targetNodeId: edgeData.targetNodeId,
        type: edgeType,
        projectId: edgeData.projectId,
        updatedAt: new Date(),
        metadata: {
          aiGenerated: edgeData.metadata?.aiGenerated || false,
          reason: edgeData.metadata?.reason || 'Manual connection',
          ...edgeData.metadata,
        },
      });
      res.json(newEdge);
    } catch (error) {
      console.error('Error creating edge:', error);
      res.status(500).json({
        error: 'Failed to create edge',
        details: (error as Error).message,
      });
    }
  });

  app.put('/edges/:id', async (req, res) => {
    try {
      const updatedEdge = await storageImpl.updateGraphEdge(
        req.params.id,
        req.body
      );
      res.json(updatedEdge);
    } catch (error) {
      console.error('Error updating edge:', error);
      res.status(500).json({
        error: 'Failed to update edge',
        details: (error as Error).message,
      });
    }
  });

  app.delete('/edges/:id', async (req, res) => {
    try {
      await storageImpl.deleteGraphEdge(req.params.id);
      res.status(204).send();
    } catch {
      res.status(500).json({ error: 'Failed to delete edge' });
    }
  });
}
