import type {
  Template,
  InsertGraphNode,
  InsertGraphEdge,
} from '@shared/schema';
import { Router, type Request, type Response } from 'express';

import { AdvancedAIAnalyzer } from '../advanced-ai-analyzer';
import { logger } from '../utils/logger';

import { AnalyzerFactory } from './analyzer-adapters';
import { FileParser } from './file-parser';
import { mergeAnalysisResults, mergeWithExisting } from './result-merger';
import type { AnalysisResult, IValidationResult, ICodeAnalyzer } from './types';

const permagraphBaseUrl =
  process.env.PERMAGRAPH_API_URL || 'http://localhost:8000';

/**
 * Central orchestrator coordinating parsing, analysis and merging.
 */
export class UnifiedASTOrchestrator {
  private analyzers: ICodeAnalyzer[] = [];
  private fileParser = new FileParser();

  constructor(
    private template: Template,
    private projectId: string,
    private analyzerTypes: string[] = ['enhanced']
  ) {
    this.initializeAnalyzers();
  }

  private initializeAnalyzers(): void {
    this.analyzers = this.analyzerTypes.map(type =>
      AnalyzerFactory.createAnalyzer(type, this.template, this.projectId)
    );
  }

  /**
   * Main orchestration method coordinating all analyzers.
   */
  async orchestrateAnalysis(
    files: Express.Multer.File[]
  ): Promise<AnalysisResult> {
    const parsedFiles = await this.fileParser.parseFiles(files);

    const results = await Promise.all(
      this.analyzers.map(async analyzer => {
        try {
          return await analyzer.analyze(parsedFiles, this.projectId);
        } catch (err) {
          return this.createEmptyResult();
        }
      })
    );

    const mergedResult = mergeAnalysisResults(results);
    const validated = await this.applyTemplateValidation(mergedResult);
    return this.enhanceWithAI(validated);
  }

  async analyzeIncremental(
    newFiles: Express.Multer.File[],
    existingNodes: InsertGraphNode[],
    existingEdges: InsertGraphEdge[]
  ): Promise<AnalysisResult> {
    const parsedFiles = await this.fileParser.parseFiles(newFiles);
    const semantic = AnalyzerFactory.createAnalyzer(
      'semantic',
      this.template,
      this.projectId
    );
    const result = await semantic.analyze(parsedFiles, this.projectId);
    return mergeWithExisting(result, existingNodes, existingEdges);
  }

  private async applyTemplateValidation(
    result: AnalysisResult
  ): Promise<AnalysisResult> {
    const templateValidations = this.validateAgainstTemplate(result);
    result.validationResults.push(...templateValidations);
    return result;
  }

  private validateAgainstTemplate(result: AnalysisResult): IValidationResult[] {
    const validations: IValidationResult[] = [];

    if (this.template.validationRules) {
      this.template.validationRules.forEach(rule => {
        const v = this.applyValidationRule(rule, result);
        if (v) validations.push(v);
      });
    }

    return validations;
  }

  private applyValidationRule(
    rule: any,
    result: AnalysisResult
  ): IValidationResult | null {
    if (
      rule.type === 'required' &&
      rule.rule === 'controller-service-separation'
    ) {
      const controllers = result.nodes.filter(n => n.type === 'controller');
      const services = result.nodes.filter(n => n.type === 'service');
      if (controllers.length > 0 && services.length === 0) {
        return {
          type: 'warning',
          message: 'Controllers detected without corresponding services',
          severity: 3,
        };
      }
    }
    return null;
  }

  private async enhanceWithAI(result: AnalysisResult): Promise<AnalysisResult> {
    try {
      const ai = new AdvancedAIAnalyzer(this.template);
      result.insights = await ai.analyzeArchitecture(
        result.nodes as any[],
        result.edges as any[],
        this.projectId
      );
    } catch {
      // best effort
    }
    return result;
  }

  private createEmptyResult(): AnalysisResult {
    return { nodes: [], edges: [], patterns: [], validationResults: [] };
  }
}

/**
 * Convenience helper used by routes.
 */
export async function orchestrateCodebaseAnalysis(
  files: Express.Multer.File[],
  template: Template,
  projectId: string,
  analyzerTypes: string[] = ['enhanced', 'semantic']
): Promise<AnalysisResult> {
  const orchestrator = new UnifiedASTOrchestrator(
    template,
    projectId,
    analyzerTypes
  );
  return await orchestrator.orchestrateAnalysis(files);
}

export * from './types';
export { AnalyzerFactory } from './analyzer-adapters';

export const orchestratorRouter = Router();

// Route to trigger document ingestion in PermaGraph
orchestratorRouter.post('/docs-ingest', async (req: Request, res: Response) => {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);

  try {
    const response = await fetch(`${permagraphBaseUrl}/api/v1/docs-ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!response.ok) {
      const text = await response.text();
      logger.error('PermaGraph ingestion failed', {
        status: response.status,
        body: text,
      });
      return res
        .status(response.status)
        .json({ error: 'Failed to ingest documents' });
    }

    const data = await response.json();
    res.status(response.status).json(data);
  } catch (error) {
    clearTimeout(timeout);
    if ((error as Error).name === 'AbortError') {
      logger.error('PermaGraph ingestion request timed out', { error });
      res.status(504).json({ error: 'PermaGraph ingestion request timed out' });
    } else {
      logger.error('PermaGraph service unreachable', { error });
      res.status(502).json({ error: 'PermaGraph service is unreachable' });
    }
  }
});
