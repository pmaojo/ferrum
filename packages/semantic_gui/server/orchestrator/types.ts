import type { InsertGraphNode, InsertGraphEdge } from '@shared/schema';
import type * as ts from 'typescript';

export interface ICodeAnalyzer {
  analyze(files: ParsedFile[], projectId: string): Promise<AnalysisResult>;
  getAnalyzerType(): string;
}

export interface IArchitecturalPattern {
  id: string;
  type: string;
  confidence: number;
  description: string;
  files: string[];
}

export interface IValidationResult {
  type: 'error' | 'warning' | 'info';
  message: string;
  filePath?: string;
  severity: number;
}

export interface AnalysisResult {
  nodes: InsertGraphNode[];
  edges: InsertGraphEdge[];
  patterns: IArchitecturalPattern[];
  validationResults: IValidationResult[];
  businessRules?: any[];
  suggestions?: string[];
  insights?: any;
}

export interface ParsedFile {
  filePath: string;
  content: string;
  ast?: ts.SourceFile;
  normalizedPath: string;
  exports: string[];
  imports: string[];
  metadata: {
    complexity: number;
    loc: number;
    dependencies: string[];
    decorators: string[];
  };
}
