import type { Template } from '@shared/schema';

import { FileParser } from '../server/orchestrator/file-parser';
import type {
  AnalysisResult,
  ParsedFile,
  ICodeAnalyzer,
} from '../server/orchestrator/types';

declare global {
  namespace Express {
    namespace Multer {
      interface File {
        originalname: string;
        buffer: Buffer;
      }
    }
  }
}

class GraphAnalyzer implements ICodeAnalyzer {
  constructor(private template: Template) {}
  async analyze(
    files: ParsedFile[],
    _projectId: string
  ): Promise<AnalysisResult> {
    return {
      nodes: files.map((f, i) => ({
        name: f.filePath,
        type: 'module',
        templateId: this.template.id,
        projectId: 'p',
        position: { x: i, y: i },
      })) as any,
      edges: [],
      patterns: [],
      validationResults: [],
    };
  }
  getAnalyzerType(): string {
    return 'graph';
  }
}

describe('project analysis end-to-end', () => {
  const template: Template = {
    id: 't',
    name: 't',
    description: '',
    nodeTypes: [],
    validationRules: [],
    metadata: {},
  } as any;

  it('parses code and generates graph nodes', async () => {
    const file = {
      originalname: 'index.ts',
      buffer: Buffer.from('export const a = 1;'),
    } as Express.Multer.File;
    const parser = new FileParser();
    const parsed = await parser.parseFiles([file]);
    const analyzer = new GraphAnalyzer(template);
    const result = await analyzer.analyze(parsed, 'p');
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].name).toBe('index.ts');
  });
});
