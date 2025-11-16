import { ProjectFS } from '../ProjectFS';
import type { IStorage } from '../../storage';

export interface FileChange {
  path: string;
  content: string;
}

export interface ApplyChangesResult {
  diffs: any[];
  linesModified: number;
  filesApplied: number;
}

export class ProjectFileService {
  constructor(private readonly storage: IStorage) {}

  async readFile(projectId: string, filePath: string): Promise<string> {
    const projectPath = await this.getProjectPath(projectId);
    const fsService = new ProjectFS(projectPath);
    return fsService.readFile(filePath);
  }

  async applyChanges(
    projectId: string,
    files: FileChange[]
  ): Promise<ApplyChangesResult> {
    const projectPath = await this.getProjectPath(projectId);
    const fsService = new ProjectFS(projectPath);
    const diffs = await fsService.applyChanges(files, false);
    let linesModified = 0;
    for (const diff of diffs) {
      linesModified += diff.diff
        .split('\n')
        .filter(
          (line: string) =>
            (line.startsWith('+') && !line.startsWith('+++')) ||
            (line.startsWith('-') && !line.startsWith('---'))
        ).length;
    }
    return {
      diffs,
      linesModified,
      filesApplied: files.length,
    };
  }

  async rollback(projectId: string): Promise<void> {
    const projectPath = await this.getProjectPath(projectId);
    const fsService = new ProjectFS(projectPath);
    await fsService.rollback();
  }

  private async getProjectPath(projectId: string): Promise<string> {
    const project = await this.storage.getProject(projectId);
    if (!project) {
      const error = new Error('Project not found');
      (error as any).status = 404;
      throw error;
    }
    return project.projectPath;
  }
}

export default ProjectFileService;
