import { promises as fs, existsSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

import Ajv, { type ValidateFunction } from 'ajv';

import type { Template } from '../shared/schema';
import type { SCGTag } from '../types/universal-tag-system';

import { featureFlagService } from './FeatureFlagService';
import { LoggerFactory } from './logging';
import { FrameworkDetector } from './tagging/FrameworkDetector';

/**
 * Service responsible for loading template metadata from the filesystem.
 * Supports JSON template definitions with inheritance and caches
 * loaded templates for subsequent requests.
 */
export class TemplateService {
  private cache: Map<string, Template> = new Map();
  private templatesDir: string;
  private logger = LoggerFactory.createServiceLogger('template');
  private validator?: ValidateFunction;

  constructor(templatesDir?: string) {
    if (templatesDir) {
      this.templatesDir = templatesDir;
    } else if (process.env.SCG_TEMPLATES_DIR) {
      this.templatesDir = process.env.SCG_TEMPLATES_DIR;
    } else {
      // Get current directory
      const __dirname = path.dirname(fileURLToPath(import.meta.url));

      // Try multiple possible paths
      const possiblePaths = [
        // Local templates directory (preferred for development)
        path.join(process.cwd(), 'templates'),
        // Docker production (compose mounts project at /app)
        '/app/templates/semantic_gui',
        // Some runtime environments may resolve __dirname to '/'
        '/templates/semantic_gui',
        // Running from project root (dev)
        path.join(process.cwd(), 'templates', 'semantic_gui'),
        path.join(process.cwd(), 'scg', 'templates', 'semantic_gui'),
        // Bundled dist layouts
        path.join(process.cwd(), 'dist', 'templates', 'semantic_gui'),
        // Relative to this file (compiled location)
        path.join(__dirname, '..', '..', '..', 'templates', 'semantic_gui'),
      ];

      // Find the first path that exists
      let foundPath = path.join(process.cwd(), 'templates');
      for (const testPath of possiblePaths) {
        try {
          // Check if directory exists synchronously for constructor
          if (existsSync(testPath)) {
            foundPath = testPath;
            break;
          }
        } catch (error) {
          // Continue to next path
        }
      }

      this.templatesDir = foundPath;
    }
    this.logger.info(
      `TemplateService using templates directory: ${this.templatesDir}`
    );
  }

  async loadTemplate(id: string): Promise<Template> {
    const cached = this.cache.get(id);
    if (cached) {
      return cached;
    }

    if (
      id.startsWith('laravel') &&
      !featureFlagService.isEnabled('laravelBeta')
    ) {
      throw new Error(`Template "${id}" is disabled`);
    }

    const template = await this.loadTemplateFile(id);
    this.cache.set(id, template);
    return template;
  }

  // Backwards compatibility
  async getTemplate(id: string): Promise<Template> {
    return this.loadTemplate(id);
  }

  async listTemplates(): Promise<Template[]> {
    const files = await fs.readdir(this.templatesDir);
    const ids = Array.from(
      new Set(
        files
          .filter(f => f.endsWith('.json'))
          .map(f => f.replace(/\.json$/i, ''))
      )
    );

    const templates: Template[] = [];
    for (const id of ids) {
      if (
        id.startsWith('laravel') &&
        !featureFlagService.isEnabled('laravelBeta')
      ) {
        continue;
      }
      try {
        const template = await this.loadTemplate(id);
        templates.push(template);
      } catch (err) {
        this.logger.error(`Failed to load template ${id}`, err as Error, {
          templateId: id,
        });
      }
    }
    return templates;
  }

  async getTemplatesByCategory(): Promise<Record<string, Template[]>> {
    const templates = await this.listTemplates();
    const categories: Record<string, Template[]> = {};

    for (const template of templates) {
      const category = this.getTemplateCategory(template);
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(template);
    }

    return categories;
  }

  async searchTemplates(query: string): Promise<Template[]> {
    const templates = await this.listTemplates();
    const lowerQuery = query.toLowerCase();

    return templates.filter(
      template =>
        template.name.toLowerCase().includes(lowerQuery) ||
        template.description.toLowerCase().includes(lowerQuery) ||
        template.metadata?.framework?.toLowerCase().includes(lowerQuery) ||
        template.metadata?.architecture?.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * Automatically detect the best template for the provided code
   */
  async getBestTemplate(
    code: string,
    filePath: string
  ): Promise<Template | null> {
    const detector = new FrameworkDetector(this);
    const result = await detector.detectFramework(code, filePath);
    if (!result.templateId || result.templateId === 'unknown') {
      return null;
    }
    try {
      return await this.loadTemplate(result.templateId);
    } catch {
      return null;
    }
  }

  /**
   * Adapt an existing template using additional configuration
   */
  adaptTemplate(template: Template, adaptation: Partial<Template>): Template {
    return this.mergeTemplates(template, adaptation as Template);
  }

  /**
   * Suggest node types based on contextual information such as file path or SCG tags
   */
  getContextualTypeSuggestions(
    template: Template,
    context: { filePath?: string; code?: string; tags?: SCGTag[] }
  ): string[] {
    const nodeTypes: any[] = template.nodeTypes || [];
    const suggestions: string[] = [];

    for (const nodeType of nodeTypes) {
      const pattern = nodeType.pattern as string | undefined;
      if (context.filePath && pattern && context.filePath.includes(pattern)) {
        suggestions.push(nodeType.type);
      } else if (context.code && pattern && context.code.includes(pattern)) {
        suggestions.push(nodeType.type);
      }
    }

    if (suggestions.length === 0) {
      return nodeTypes.map((t: any) => t.type);
    }
    return suggestions;
  }

  private async getValidator(): Promise<ValidateFunction> {
    if (!this.validator) {
      const schemaPath = path.join(this.templatesDir, 'template.schema.json');
      const schemaRaw = await fs.readFile(schemaPath, 'utf-8');
      const ajv = new Ajv({ allErrors: true, strict: false });
      this.validator = ajv.compile(JSON.parse(schemaRaw));
    }
    return this.validator;
  }

  async validateTemplate(
    file: string,
    data?: unknown
  ): Promise<{ valid: boolean; errors?: string[] }> {
    try {
      const validator = await this.getValidator();
      const json = data ?? JSON.parse(await fs.readFile(file, 'utf-8'));
      const valid = validator(json);
      const errors =
        !valid && validator.errors
          ? validator.errors.map(e => `${e.instancePath} ${e.message}`)
          : undefined;
      if (!valid) {
        this.logger.error(`Template validation failed`, undefined, {
          templateFile: path.basename(file),
          validationErrors: errors,
        });
      }
      return { valid: !!valid, errors };
    } catch (err: any) {
      this.logger.error(`Template validation error`, err, {
        templateFile: path.basename(file),
      });
      return { valid: false, errors: [err.message] };
    }
  }

  async getTemplatesHealth(): Promise<
    { id: string; valid: boolean; errors?: string[] }[]
  > {
    const files = await fs.readdir(this.templatesDir);
    const jsonFiles = files.filter(f => f.endsWith('.json'));
    const results: { id: string; valid: boolean; errors?: string[] }[] = [];
    for (const file of jsonFiles) {
      const filePath = path.join(this.templatesDir, file);
      const { valid, errors } = await this.validateTemplate(filePath);
      results.push({ id: file.replace(/\.json$/i, ''), valid, errors });
    }
    return results;
  }

  private getTemplateCategory(template: Template): string {
    const { metadata } = template;
    if (metadata?.framework) {
      return (
        metadata.framework.charAt(0).toUpperCase() + metadata.framework.slice(1)
      );
    }
    if (metadata?.architecture) {
      return (
        metadata.architecture.charAt(0).toUpperCase() +
        metadata.architecture.slice(1)
      );
    }
    return 'General';
  }

  private async loadTemplateFile(id: string): Promise<Template> {
    const jsonPath = path.join(this.templatesDir, `${id}.json`);
    try {
      const data = await fs.readFile(jsonPath, 'utf-8');
      const template = JSON.parse(data) as Template;
      const { valid, errors } = await this.validateTemplate(jsonPath, template);
      if (!valid) {
        throw new Error(errors?.join(', ') || 'Template validation failed');
      }

      // Handle template inheritance
      if (template.extends) {
        const baseTemplate = await this.loadTemplate(template.extends);
        return this.mergeTemplates(baseTemplate, template);
      }

      return template;
    } catch (error: any) {
      throw new Error(
        `Template "${id}" not found or invalid: ${error.message}`
      );
    }
  }

  private mergeTemplates(base: Template, child: Template): Template {
    return {
      ...base,
      ...child,
      nodeTypes: this.mergeByKey(base.nodeTypes, child.nodeTypes, 'type'),
      relations: this.mergeByKey(
        base.relations || [],
        child.relations || [],
        (r: any) => `${r.source}-${r.target}-${r.type}`
      ),
      validationRules: this.mergeByKey(
        base.validationRules,
        child.validationRules,
        'rule'
      ),
      metadata: { ...base.metadata, ...child.metadata },
    };
  }

  private mergeByKey<T>(
    baseArr: T[] = [],
    childArr: T[] = [],
    key: string | ((item: T) => string)
  ): T[] {
    const getter = typeof key === 'function' ? key : (item: any) => item[key];
    const map = new Map<string, T>();
    for (const item of baseArr) {
      map.set(getter(item), item);
    }
    for (const item of childArr) {
      map.set(getter(item), item);
    }
    return Array.from(map.values());
  }

  static async mergeTemplate(
    template: Template,
    templatesDir?: string
  ): Promise<Template> {
    if (!template.extends) {
      return template;
    }
    const service = new TemplateService(templatesDir);
    const base = await service.loadTemplate(template.extends);
    return service.mergeTemplates(base, template);
  }
}

export default TemplateService;
