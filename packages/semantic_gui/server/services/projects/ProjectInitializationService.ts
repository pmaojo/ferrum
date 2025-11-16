import fs from 'node:fs';
import path from 'node:path';

import type { PermaGraphService } from './PermaGraphService';

export class ProjectInitializationService {
  constructor(private readonly permaGraphService: PermaGraphService) {}

  async initialize(projectId: string, projectPath: string): Promise<void> {
    await this.permaGraphService.init(projectId, projectPath);
    const docs = await this.readRequirementDocs(projectPath);
    if (docs.length) {
      await this.permaGraphService.ingestDocs(projectId, docs);
    }
    await this.permaGraphService.sync(projectId, 'full');
  }

  private async readRequirementDocs(
    projectPath: string
  ): Promise<{ name: string; content: string }[]> {
    const docsDir = path.join(projectPath, 'docs', 'requirements');
    try {
      const files = await fs.promises.readdir(docsDir);
      const docs = await Promise.all(
        files
          .filter(file => file.endsWith('.md'))
          .map(async file => ({
            name: file,
            content: await fs.promises.readFile(path.join(docsDir, file), 'utf8'),
          }))
      );
      return docs;
    } catch {
      return [];
    }
  }
}

export default ProjectInitializationService;
