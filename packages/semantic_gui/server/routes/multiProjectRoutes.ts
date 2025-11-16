import express from 'express';

import { ProjectController } from '../controllers/multi-project/ProjectController';
import { TemplateController } from '../controllers/multi-project/TemplateController';
import { TenantController } from '../controllers/multi-project/TenantController';
import { createPermaGraphMultiProjectClient } from '../services/permaGraphMultiProjectClient';

const router = express.Router();

const client = createPermaGraphMultiProjectClient();
const projectController = new ProjectController(client);
const templateController = new TemplateController(client);
const tenantController = new TenantController(client);

router.get('/', projectController.listProjects);
router.post('/', projectController.createProject);

router.get('/templates', templateController.listTemplates);
router.post('/templates', templateController.createTemplate);

router.get('/tenants/:tenantId/projects', tenantController.listTenantProjects);

router.post('/compare', projectController.compareProjects);
router.post('/bulk', projectController.bulkOperation);
router.post('/clone', projectController.cloneProject);

router.get('/:projectId/statistics', projectController.getProjectStatistics);
router.get('/:projectId/activity', projectController.getProjectActivity);
router.post('/:projectId/switch', projectController.switchProject);
router.post('/:projectId/archive', projectController.archiveProject);
router.delete('/:projectId', projectController.deleteProject);
router.put('/:projectId', projectController.updateProject);
router.get('/:projectId', projectController.getProject);

export default router;
