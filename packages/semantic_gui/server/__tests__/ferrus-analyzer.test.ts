import type { Template } from '@shared/schema';

import type { ParsedFile } from '../orchestrator';
import { FerrusAnalyzerAdapter } from '../orchestrator/analyzer-adapters';

describe('FerrusAnalyzerAdapter', () => {
  const template: Template = {
    id: 't',
    name: 'Ferrus',
    description: '',
    nodeTypes: [],
    validationRules: [],
    metadata: {},
  };

  const makeFile = (filePath: string, content: string): ParsedFile => ({
    filePath,
    content,
    normalizedPath: filePath,
    exports: [],
    imports: [],
    metadata: { complexity: 0, loc: 0, dependencies: [], decorators: [] },
  });

  it('extracts nodes, edges and validations from Rust code', async () => {
    const files: ParsedFile[] = [
      makeFile(
        'src/main.rs',
        `mod utils;\nfn main() { utils::helper(); let x = Some(1).unwrap(); }`
      ),
      makeFile('src/utils.rs', `pub fn helper() {}`),
    ];

    const adapter = new FerrusAnalyzerAdapter(template, 'p');
    const result = await adapter.analyze(files);

    const nodeNames = result.nodes.map(n => n.name);
    expect(nodeNames).toEqual(expect.arrayContaining(['main', 'helper']));
    expect(result.edges.length).toBeGreaterThan(0);
    expect(result.validationResults.length).toBeGreaterThan(0);
  });
});
