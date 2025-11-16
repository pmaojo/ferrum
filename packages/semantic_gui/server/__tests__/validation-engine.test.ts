import type { GraphNode, Template } from '@shared/schema';

import { ValidationEngine } from '../validation-engine';

describe('ValidationEngine.validateArchitecture', () => {
  const baseTemplate: Template = {
    id: 'tpl',
    name: 'tpl',
    description: '',
    nodeTypes: [],
    validationRules: [],
    metadata: {},
  };

  it('rewards controllers following conventions', () => {
    const engine = new ValidationEngine(baseTemplate);
    const nodes: GraphNode[] = [
      {
        id: '1',
        name: 'UserController',
        type: 'controller',
        filePath: 'src/controllers/user.controller.ts',
        templateId: 'tpl',
        projectId: 'p',
        position: { x: 0, y: 0 },
        metadata: { decorators: ['Controller'] },
        description: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    ];

    const result = engine.validateArchitecture(nodes, [], 'p');
    expect(result.rewards.some(r => r.ruleId === 'controller-naming')).toBe(
      true
    );
    expect(result.rewards.some(r => r.ruleId === 'controller-naming')).toBe(
      true
    );
    expect(result.penalties.length).toBe(0);
  });

  it('detects controller naming and decorator violations', () => {
    const engine = new ValidationEngine(baseTemplate);
    const nodes: GraphNode[] = [
      {
        id: '1',
        name: 'User',
        type: 'controller',
        filePath: 'src/controllers/user.ts',
        templateId: 'tpl',
        projectId: 'p',
        position: { x: 0, y: 0 },
        metadata: { decorators: [] },
        description: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    ];

    const result = engine.validateArchitecture(nodes, [], 'p');
    const naming = result.penalties.find(p => p.ruleId === 'controller-naming');
    const decorator = result.penalties.find(
      p => p.ruleId === 'controller-decorator'
    );
    expect(naming).toBeDefined();
    expect(decorator).toBeDefined();
    expect(result.violations.length).toBeGreaterThanOrEqual(1);
  });

  it('emits events for violations and completion', () => {
    const engine = new ValidationEngine(baseTemplate);
    const nodes: GraphNode[] = [
      {
        id: '1',
        name: 'User',
        type: 'controller',
        filePath: 'src/controllers/user.ts',
        templateId: 'tpl',
        projectId: 'p',
        position: { x: 0, y: 0 },
        metadata: { decorators: [] },
        description: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      },
    ];

    const found: unknown[] = [];
    let completed = false;
    engine.on('violation-found', v => found.push(v));
    engine.on('validation-completed', () => {
      completed = true;
    });

    engine.validateArchitecture(nodes, [], 'p');

    expect(found.length).toBeGreaterThan(0);
    expect(completed).toBe(true);
  });
});
