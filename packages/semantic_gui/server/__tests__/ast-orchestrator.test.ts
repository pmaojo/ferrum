import type {
  Template,
  InsertGraphNode,
  InsertGraphEdge,
} from '@shared/schema';

import {
  orchestrateCodebaseAnalysis,
  AnalyzerFactory,
  UnifiedASTOrchestrator,
} from '../orchestrator';
import type {
  AnalysisResult,
  ParsedFile,
  ICodeAnalyzer,
} from '../orchestrator';

class MockAnalyzer implements ICodeAnalyzer {
  constructor(
    private name: string,
    private result: AnalysisResult
  ) {}
  async analyze(_files: ParsedFile[]): Promise<AnalysisResult> {
    return this.result;
  }
  getAnalyzerType(): string {
    return this.name;
  }
}

describe('orchestrateCodebaseAnalysis', () => {
  const template: Template = {
    id: 't',
    name: 't',
    description: '',
    nodeTypes: [],
    validationRules: [],
    metadata: {},
  };

  const nodeA1: InsertGraphNode = {
    name: 'A',
    type: 'controller',
    templateId: 't',
    projectId: 'p',
    position: { x: 0, y: 0 },
  } as any;
  const nodeA2: InsertGraphNode = {
    name: 'A',
    type: 'controller',
    templateId: 't',
    projectId: 'p',
    position: { x: 1, y: 1 },
  } as any;
  const edge1: InsertGraphEdge = {
    id: 'e1',
    sourceNodeId: 'n1',
    targetNodeId: 'n2',
    type: 'uses',
    projectId: 'p',
    createdAt: '',
    metadata: {},
  } as any;
  const edge2: InsertGraphEdge = {
    id: 'e2',
    sourceNodeId: 'n2',
    targetNodeId: 'n1',
    type: 'calls',
    projectId: 'p',
    createdAt: '',
    metadata: {},
  } as any;

  const result1: AnalysisResult = {
    nodes: [nodeA1],
    edges: [edge1],
    patterns: [],
    validationResults: [],
  };
  const result2: AnalysisResult = {
    nodes: [nodeA2],
    edges: [edge2],
    patterns: [],
    validationResults: [],
  };

  beforeAll(() => {
    jest
      .spyOn(AnalyzerFactory, 'createAnalyzer')
      .mockImplementation((type: string) => {
        if (type === 'first') return new MockAnalyzer('first', result1);
        return new MockAnalyzer('second', result2);
      });
    jest
      .spyOn(UnifiedASTOrchestrator.prototype as any, 'enhanceWithAI')
      .mockImplementation(async (_r: any) => _r);
  });

  afterAll(() => jest.restoreAllMocks());

  it('merges analyzer results', async () => {
    const file = {
      originalname: 'file.ts',
      buffer: Buffer.from('export const x=1;'),
    } as Express.Multer.File;
    const res = await orchestrateCodebaseAnalysis([file], template, 'p', [
      'first',
      'second',
    ]);

    expect(res.nodes).toHaveLength(1);
    expect(res.nodes[0].name).toBe('A');
    expect(res.edges).toHaveLength(2);
  });
});
