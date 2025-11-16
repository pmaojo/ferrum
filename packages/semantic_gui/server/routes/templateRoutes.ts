import { Router } from 'express';

import { TemplateService } from '../services/TemplateService';

const router = Router();
const templateService = new TemplateService();

// Get all templates
router.get('/', async (req, res) => {
  try {
    const templates = await templateService.listTemplates();
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get templates by category
router.get('/categories', async (req, res) => {
  try {
    const categories = await templateService.getTemplatesByCategory();
    res.json(categories);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Search templates
router.get('/search', async (req, res) => {
  try {
    const query = req.query.q as string;
    if (!query) {
      return res.status(400).json({ error: 'Query parameter "q" is required' });
    }
    const templates = await templateService.searchTemplates(query);
    res.json(templates);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get template validation status
router.get('/health', async (_req, res) => {
  try {
    const health = await templateService.getTemplatesHealth();
    res.json(health);
  } catch (error) {
    res.status(500).json({ error: (error as Error).message });
  }
});

// Get specific template
router.get('/:id', async (req, res) => {
  try {
    const template = await templateService.getTemplate(req.params.id);
    res.json(template);
  } catch (error) {
    res.status(404).json({ error: error.message });
  }
});

export default router;
