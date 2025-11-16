import * as ts from 'typescript';

import type { ParsedFile } from './types';

/**
 * Parses uploaded files into normalized internal representation.
 * Extracts AST, imports/exports and basic metrics for later analyzers.
 */
export class FileParser {
  async parseFiles(files: Express.Multer.File[]): Promise<ParsedFile[]> {
    return files.map(file => this.parseFile(file));
  }

  private parseFile(file: Express.Multer.File): ParsedFile {
    const content = file.buffer.toString();
    const normalizedPath = this.normalizePath(file.originalname);

    return {
      filePath: file.originalname,
      content,
      normalizedPath,
      ast: this.parseToAST(content, file.originalname),
      exports: this.extractExports(content),
      imports: this.extractImports(content),
      metadata: {
        complexity: this.calculateComplexity(content),
        loc: content.split('\n').length,
        dependencies: this.extractDependencies(content),
        decorators: this.extractDecorators(content),
      },
    };
  }

  private parseToAST(
    content: string,
    fileName: string
  ): ts.SourceFile | undefined {
    try {
      return ts.createSourceFile(
        fileName,
        content,
        ts.ScriptTarget.Latest,
        true
      );
    } catch {
      return undefined;
    }
  }

  private normalizePath(filePath: string): string {
    return filePath.replace(/\\/g, '/').toLowerCase();
  }

  private extractExports(content: string): string[] {
    const exportMatches = content.match(
      /export\s+(?:class|function|interface|const|let|var)\s+(\w+)/g
    );
    return exportMatches
      ? exportMatches.map(m => m.split(/\s+/).pop() || '')
      : [];
  }

  private extractImports(content: string): string[] {
    const importMatches = content.match(/import.*from\s+['"](.+)['"]/g);
    return importMatches
      ? importMatches
          .map(m => {
            const match = m.match(/from\s+['"](.+)['"]/);
            return match ? match[1] : '';
          })
          .filter(Boolean)
      : [];
  }

  private calculateComplexity(content: string): number {
    const factors = ['if', 'else', 'while', 'for', 'switch', 'case', 'catch'];
    let complexity = 1;
    factors.forEach(f => {
      const matches = content.match(new RegExp(`\\b${f}\\b`, 'g'));
      if (matches) complexity += matches.length;
    });
    return complexity;
  }

  private extractDependencies(content: string): string[] {
    return this.extractImports(content).filter(imp => imp.startsWith('.'));
  }

  private extractDecorators(content: string): string[] {
    const decoratorMatches = content.match(/@(\w+)/g);
    return decoratorMatches ? decoratorMatches.map(m => m.substring(1)) : [];
  }
}
