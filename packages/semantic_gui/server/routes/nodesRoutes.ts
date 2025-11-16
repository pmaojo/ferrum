import { insertGraphNodeSchema } from '@shared/schema';
import type { Router } from 'express';

import type { IStorage } from '../storage';
import { ValidationEngine } from '../validation-engine';

export function attachNodeRoutes(app: Router, storageImpl: IStorage) {
  app.post('/nodes', async (req, res) => {
    try {
      const nodeData = {
        ...req.body,
        id:
          req.body.id ||
          `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        metadata: req.body.metadata || {},
        description: req.body.description || `${req.body.type} component`,
        filePath:
          req.body.filePath ||
          `src/${req.body.type}s/${req.body.name}.${req.body.type}.ts`,
        sourceMap: req.body.sourceMap || null,
      };
      const data = insertGraphNodeSchema.parse(nodeData) as any;
      const template = await storageImpl.getTemplate(data.templateId);
      if (!template) {
        return res.status(404).json({ error: 'Template not found' });
      }
      const validationEngine = new ValidationEngine(template);
      const mockNodes = [{ ...data, id: data.id }] as any[];
      const preliminaryValidation = validationEngine.validateArchitecture(
        mockNodes,
        [],
        data.projectId
      );
      const criticalViolations = preliminaryValidation.penalties.filter(
        p => p.severity === 'critical'
      );
      if (criticalViolations.length > 0) {
        return res.status(400).json({
          error: 'NestJS Best Practice Violation',
          penalties: criticalViolations,
          pointsLost: criticalViolations.reduce(
            (sum, p) => sum + p.pointsLost,
            0
          ),
          suggestions: criticalViolations.map(v => v.suggestion),
        });
      }
      const node = await storageImpl.createGraphNode(data);
      res.json(node);
    } catch (error: any) {
      console.error('Node creation error:', error);
      res.status(400).json({
        error: 'Invalid node data',
        details: error.message,
        received: req.body,
      });
    }
  });

  app.put('/nodes/:id', async (req, res) => {
    try {
      const updates = insertGraphNodeSchema.partial().parse(req.body);
      const node = await storageImpl.updateGraphNode(req.params.id, updates);
      res.json(node);
    } catch {
      res.status(400).json({ error: 'Invalid node update data' });
    }
  });

  app.get('/projects/:id/nodes', async (req, res) => {
    try {
      const nodes = await storageImpl.getNodesByProject(req.params.id);
      res.json(nodes);
    } catch {
      res.status(500).json({ error: 'Failed to get nodes' });
    }
  });

  app.delete('/nodes/:id', async (req, res) => {
    try {
      await storageImpl.deleteGraphNode(req.params.id);
      res.status(204).send();
    } catch {
      res.status(500).json({ error: 'Failed to delete node' });
    }
  });
}
