import Ajv from 'ajv';
import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import client from 'prom-client';
import ProjectFS from '../services/ProjectFS';
import type { GeneratedFile } from '../services/diff/DiffService';
import { featureFlagService } from '../services/FeatureFlagService';

import { authMiddleware } from '../middleware/auth';
import { requireRole } from '../middleware/requireRole';
import type { CLIExecutor } from '../services/cli/CLIExecutor';
import { TemplateService } from '../services/TemplateService';
import type { IStorage } from '../storage';
import { errorResponse } from '../utils/error-response';
import { logger } from '../utils/logger';

const router = Router();
const ajv = new Ajv();
const templateService = new TemplateService();

const cliDuration =
  (client.register.getSingleMetric('cli_duration_seconds') as client.Histogram) ||
  new client.Histogram({
    name: 'cli_duration_seconds',
    help: 'Duration of CLI operations in seconds',
    labelNames: ['operation', 'projectId'],
  });

const cliExitCodeGauge =
  (client.register.getSingleMetric('cli_exit_code') as client.Gauge) ||
  new client.Gauge({
    name: 'cli_exit_code',
    help: 'Exit code of CLI operations',
    labelNames: ['operation', 'projectId'],
  });

const cliLimiter = rateLimit({
  windowMs: 60_000,
  max: () => Number(process.env.CLI_RATE_LIMIT_MAX || '5'),
});

router.use(authMiddleware, requireRole('owner', 'reader'), cliLimiter);

function normalizeSchema(schema: any) {
  if (!schema) return undefined;
  if (schema.type || schema.properties) return schema;
  const props = schema;
  const required = Object.keys(props).filter(
    k => !(props[k] && 'const' in props[k])
  );
  return {
    type: 'object',
    properties: props,
    required,
    additionalProperties: false,
  };
}

function extractConstArgs(schema: any): Record<string, any> {
  if (!schema) return {};
  const props = schema.properties || schema;
  const result: Record<string, any> = {};
  for (const [key, val] of Object.entries<any>(props)) {
    if (val && typeof val === 'object' && 'const' in val) {
      result[key] = val.const;
    }
  }
  return result;
}

function filterArgsSchema(schema: any, config: Record<string, any>) {
  if (!schema) return undefined;
  const filtered = { ...schema };
  const props: Record<string, any> = { ...schema.properties };
  const required: string[] | undefined = schema.required
    ? [...schema.required]
    : undefined;

  for (const key of Object.keys(props)) {
    if (config[key] !== undefined) {
      delete props[key];
      if (required) {
        const idx = required.indexOf(key);
        if (idx !== -1) required.splice(idx, 1);
      }
    }
  }

  filtered.properties = props;
  if (required) filtered.required = required;

  if (Object.keys(filtered.properties || {}).length === 0) {
    delete filtered.properties;
    delete filtered.required;
  }
  return filtered;
}

function buildCommand(
  cli: any,
  operationConfig: any,
  args: Record<string, any>
) {
  if (operationConfig.command) {
    let cmd = operationConfig.command as string;
    cmd = cmd.replace(/\{(\w+)\}/g, (_, k) => args[k] ?? '');
    return cmd;
  }
  const parts: string[] = [];
  const binary = cli?.binary;
  if (binary) parts.push(binary);
  if (operationConfig.cmd) parts.push(operationConfig.cmd);
  if (operationConfig.flags) parts.push(...operationConfig.flags);
  const constArgs = extractConstArgs(operationConfig.argsSchema);
  const merged = { ...constArgs, ...args };
  for (const value of Object.values(merged)) {
    parts.push(String(value));
  }
  return parts.join(' ').trim();
}

router.post('/projects/:id/cli/execute', async (req, res) => {
  const { id } = req.params;
  const { operation, args = {}, applyMode = 'write' } = req.body as {
    operation: string;
    args?: Record<string, any>;
    applyMode?: 'diff' | 'write' | 'pr';
  };
  const dryRun = applyMode !== 'write';
  const traceId = req.headers['x-trace-id'] as string;
  const storage = req.app.get('storage') as IStorage | undefined;
  const wsManager = req.app.get('wsManager');
  const cliExecutor = req.app.get('cliExecutor') as CLIExecutor;

  if (!traceId) {
    return errorResponse(res, 400, 'Missing traceId');
  }

  if (!storage) {
    logger.error('Storage not configured', { traceId });
    return errorResponse(res, 500, 'Storage not configured');
  }

  try {
    const project = await storage.getProject(id);
    if (!project) {
      return errorResponse(res, 404, 'Project not found');
    }
    const projectPath = project.projectPath;

    const template = await templateService.getTemplate(project.templateId);
    const cliConfig = template?.cli || {};
    const operationConfig = cliConfig.operations?.[operation];
    if (!operationConfig) {
      return errorResponse(res, 400, `Unknown operation: ${operation}`);
    }

    const projectConfig = project.metadata?.config || {};
    const mergedArgs = { ...projectConfig, ...args };

    if (operationConfig.argsSchema) {
      const schema = normalizeSchema(operationConfig.argsSchema);
      const validate = ajv.compile(schema);

      if (!validate(mergedArgs)) {
        return errorResponse(
          res,
          400,
          'Invalid arguments',
          undefined,
          validate.errors
        );
      }
    }

    const command = buildCommand(cliConfig, operationConfig, mergedArgs);

    logger.info('Executing CLI command', {
      traceId,
      cliCmd: command,
      projectId: id,
    });

    const start = Date.now();
    const execResult = await cliExecutor.execute(
      id,
      command,
      traceId,
      projectPath
    );
    const durationSeconds = (Date.now() - start) / 1000;
    cliDuration.labels({ operation, projectId: id }).observe(durationSeconds);
    cliExitCodeGauge
      .labels({ operation, projectId: id })
      .set(execResult.exitCode);

    const streaming = featureFlagService.isEnabled('cliStreaming');
    if (streaming) {
      wsManager?.broadcastToProject(id, {
        type: 'cli.done',
        projectId: id,
        data: execResult,
        timestamp: new Date().toISOString(),
      });
    }
    logger.info('CLI command finished', {
      traceId,
      cliCmd: command,
      exitCode: execResult.exitCode,
    });

    const result = execResult;
    let files: GeneratedFile[] | undefined;
    try {
      const parsed = JSON.parse(execResult.stdout);
      files = parsed.files ?? parsed;
    } catch {}

    if (files?.length) {
      try {
        const fsService = new ProjectFS(projectPath);
        const diffs = await fsService.applyChanges(files, dryRun);
        if (dryRun) {
          return res.json(diffs);
        }
        return res.json({ ...result, diffs });
      } catch (err: any) {
        if (err.status === 403) {
          return errorResponse(res, 403, 'Forbidden path');
        }
        throw err;
      }
    }
    res.json(result);
  } catch (error) {
    logger.error('CLI execution error', {
      traceId,
      cliCmd: operation,
      error: (error as Error).message,
    });
    errorResponse(res, 500, 'CLI execution failed');
  }
});

// Ability to cancel a running CLI command
router.post('/projects/:id/cli/cancel', (req, res) => {
  const traceId = req.headers['x-trace-id'] as string;
  const cliExecutor = req.app.get('cliExecutor') as CLIExecutor;

  if (!traceId) {
    return errorResponse(res, 400, 'Missing traceId');
  }

  const cancelled = cliExecutor.cancel(traceId);
  if (cancelled) {
    res.json({ cancelled: true });
  } else {
    errorResponse(res, 404, 'Process not found');
  }
});

// Get available CLI operations for a project
router.get('/projects/:id/cli/operations', async (req, res) => {
  const { id } = req.params;
  const storage = req.app.get('storage') as IStorage | undefined;

  if (!storage) {
    return errorResponse(res, 500, 'Storage not configured');
  }

  try {
    const project = await storage.getProject(id);
    if (!project) {
      return errorResponse(res, 404, 'Project not found');
    }

    const template = await templateService.getTemplate(project.templateId);
    if (!template) {
      return errorResponse(res, 404, 'Template not found');
    }

    const operations = [] as any[];
    const cli = template.cli || {};
    const projectConfig = (project as any).metadata?.config || {};

    if (cli.operations) {
      for (const [key, op] of Object.entries<any>(cli.operations)) {
        operations.push({
          key,
          label: key,
          description: op.description,
          command: buildCommand(cli, op, {}),
          argsSchema: filterArgsSchema(
            normalizeSchema(op.argsSchema),
            projectConfig
          ),
        });
      }
    }

    if (cli.commands) {
      for (const [key, op] of Object.entries<any>(cli.commands)) {
        operations.push({
          key,
          label: key,
          description: op.description,
          command: op.command,
          argsSchema: filterArgsSchema(
            normalizeSchema(op.argsSchema),
            projectConfig
          ),
        });
      }
    }

    if (cli.planGraph) {
      operations.push({
        key: 'planGraph',
        label: 'Plan Architecture',
        description: 'Generate architecture graph from codebase',
        command: cli.planGraph,
      });
    }

    if (cli.validate) {
      operations.push({
        key: 'validate',
        label: 'Validate Architecture',
        description: 'Check architecture compliance',
        command: cli.validate,
      });
    }

    res.json({
      templateId: project.templateId,
      templateName: template.name,
      operations,
    });
  } catch (error) {
    console.error('Get CLI operations error:', error);
    errorResponse(
      res,
      500,
      error instanceof Error ? error.message : 'Unknown error'
    );
  }
});

export default router;
