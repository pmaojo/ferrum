import { readFile } from 'fs/promises';
import { join, relative } from 'path';

import { LoggerFactory } from './logging/LoggerFactory';

export interface GoFile {
  path: string;
  packageName: string;
  imports: GoImport[];
  types: GoType[];
  functions: GoFunction[];
  variables: GoVariable[];
  constants: GoConstant[];
  comments: GoComment[];
  kthuluTags: KthuluTag[];
}

export interface GoImport {
  path: string;
  alias?: string;
  isLocal: boolean;
}

export interface GoType {
  name: string;
  kind: 'struct' | 'interface' | 'alias' | 'func';
  fields?: GoField[];
  methods?: GoMethod[];
  implements?: string[];
  embeds?: string[];
}

export interface GoField {
  name: string;
  type: string;
  tags?: string;
}

export interface GoMethod {
  name: string;
  receiver?: string;
  parameters: GoParameter[];
  returns: GoParameter[];
  isExported: boolean;
}

export interface GoFunction {
  name: string;
  parameters: GoParameter[];
  returns: GoParameter[];
  isExported: boolean;
  isConstructor: boolean;
}

export interface GoParameter {
  name: string;
  type: string;
}

export interface GoVariable {
  name: string;
  type: string;
  value?: string;
  isExported: boolean;
}

export interface GoConstant {
  name: string;
  type: string;
  value: string;
  isExported: boolean;
}

export interface GoComment {
  text: string;
  line: number;
  isDoc: boolean;
}

export interface KthuluTag {
  type: 'module' | 'extend' | 'shadow' | 'wrap';
  target: string;
  line: number;
}

export interface KthuluArchitectureElement {
  id: string;
  name: string;
  type:
    | 'module'
    | 'usecase'
    | 'adapter'
    | 'port'
    | 'entity'
    | 'handler'
    | 'service';
  filePath: string;
  packagePath: string;
  dependencies: string[];
  implements: string[];
  usedBy: string[];
  metadata: {
    isExported: boolean;
    hasTests: boolean;
    complexity: number;
    kthuluTags: KthuluTag[];
    fxProvides?: string[];
    fxInvokes?: string[];
  };
}

export class GoASTParser {
  private projectRoot: string;
  private logger = LoggerFactory.createUtilityLogger('go-ast-parser');

  constructor(projectRoot: string) {
    this.projectRoot = projectRoot;
  }

  /**
   * Parse a Go file and extract architectural information
   */
  async parseFile(filePath: string): Promise<GoFile> {
    const content = await readFile(filePath, 'utf-8');
    const relativePath = relative(this.projectRoot, filePath);

    return {
      path: relativePath,
      packageName: this.extractPackageName(content),
      imports: this.extractImports(content),
      types: this.extractTypes(content),
      functions: this.extractFunctions(content),
      variables: this.extractVariables(content),
      constants: this.extractConstants(content),
      comments: this.extractComments(content),
      kthuluTags: this.extractKthuluTags(content),
    };
  }

  /**
   * Analyze Kthulu project structure and extract architectural elements
   */
  async analyzeKthuluProject(
    projectPath: string
  ): Promise<KthuluArchitectureElement[]> {
    const modulesPath = join(projectPath, 'backend', 'internal', 'modules');
    const usecasePath = join(projectPath, 'backend', 'internal', 'usecase');
    const adaptersPath = join(projectPath, 'backend', 'internal', 'adapters');
    const domainPath = join(projectPath, 'backend', 'internal', 'domain');

    const [moduleElements, usecaseElements, adapterElements, domainElements] =
      await Promise.all([
        this.analyzeModules(modulesPath).catch(err => {
          throw new Error(
            `Failed to analyze modules at ${modulesPath}: ${err instanceof Error ? err.message : String(err)}`
          );
        }),
        this.analyzeUseCases(usecasePath).catch(err => {
          throw new Error(
            `Failed to analyze use cases at ${usecasePath}: ${err instanceof Error ? err.message : String(err)}`
          );
        }),
        this.analyzeAdapters(adaptersPath).catch(err => {
          throw new Error(
            `Failed to analyze adapters at ${adaptersPath}: ${err instanceof Error ? err.message : String(err)}`
          );
        }),
        this.analyzeDomain(domainPath).catch(err => {
          throw new Error(
            `Failed to analyze domain entities at ${domainPath}: ${err instanceof Error ? err.message : String(err)}`
          );
        }),
      ]);

    return [
      ...moduleElements,
      ...usecaseElements,
      ...adapterElements,
      ...domainElements,
    ];
  }

  private async analyzeModules(
    modulesPath: string
  ): Promise<KthuluArchitectureElement[]> {
    const elements: KthuluArchitectureElement[] = [];

    try {
      const { readdir } = await import('fs/promises');
      const files = await readdir(modulesPath);

      for (const file of files) {
        if (file.endsWith('.go') && !file.endsWith('_test.go')) {
          const filePath = join(modulesPath, file);
          const goFile = await this.parseFile(filePath);

          // Look for module definitions (fx.Options variables)
          const moduleVars = goFile.variables.filter(
            v => v.name.endsWith('Module') && v.type.includes('fx.Options')
          );

          for (const moduleVar of moduleVars) {
            const moduleName = moduleVar.name
              .replace('Module', '')
              .toLowerCase();
            const kthuluTag = goFile.kthuluTags.find(
              tag => tag.type === 'module' && tag.target === moduleName
            );

            elements.push({
              id: `module-${moduleName}`,
              name: moduleName,
              type: 'module',
              filePath: goFile.path,
              packagePath: goFile.packageName,
              dependencies: this.extractModuleDependencies(goFile),
              implements: [],
              usedBy: [],
              metadata: {
                isExported: moduleVar.isExported,
                hasTests: files.some(
                  f => f === `${file.replace('.go', '_test.go')}`
                ),
                complexity: this.calculateComplexity(goFile),
                kthuluTags: kthuluTag ? [kthuluTag] : [],
                fxProvides: this.extractFxProvides(goFile),
                fxInvokes: this.extractFxInvokes(goFile),
              },
            });
          }
        }
      }
    } catch (error) {
      this.logger.error('Error analyzing modules', error as Error);
    }

    return elements;
  }

  private async analyzeUseCases(
    usecasePath: string
  ): Promise<KthuluArchitectureElement[]> {
    const elements: KthuluArchitectureElement[] = [];

    try {
      const { readdir } = await import('fs/promises');
      const files = await readdir(usecasePath);

      for (const file of files) {
        if (file.endsWith('.go') && !file.endsWith('_test.go')) {
          const filePath = join(usecasePath, file);
          const goFile = await this.parseFile(filePath);

          // Look for UseCase structs
          const usecaseTypes = goFile.types.filter(
            t => t.kind === 'struct' && t.name.endsWith('UseCase')
          );

          for (const usecaseType of usecaseTypes) {
            const usecaseName = usecaseType.name
              .replace('UseCase', '')
              .toLowerCase();

            elements.push({
              id: `usecase-${usecaseName}`,
              name: usecaseType.name,
              type: 'usecase',
              filePath: goFile.path,
              packagePath: goFile.packageName,
              dependencies: this.extractTypeDependencies(usecaseType, goFile),
              implements: usecaseType.implements || [],
              usedBy: [],
              metadata: {
                isExported: this.isExported(usecaseType.name),
                hasTests: files.some(
                  f => f === `${file.replace('.go', '_test.go')}`
                ),
                complexity: this.calculateTypeComplexity(usecaseType),
                kthuluTags: goFile.kthuluTags,
              },
            });
          }
        }
      }
    } catch (error) {
      this.logger.error('Error analyzing use cases', error as Error);
    }

    return elements;
  }

  private async analyzeAdapters(
    adaptersPath: string
  ): Promise<KthuluArchitectureElement[]> {
    const elements: KthuluArchitectureElement[] = [];

    try {
      const { readdir } = await import('fs/promises');
      const subdirs = await readdir(adaptersPath);

      for (const subdir of subdirs) {
        const subdirPath = join(adaptersPath, subdir);
        const { stat } = await import('fs/promises');
        const stats = await stat(subdirPath);

        if (stats.isDirectory()) {
          const files = await readdir(subdirPath);

          for (const file of files) {
            if (file.endsWith('.go') && !file.endsWith('_test.go')) {
              const filePath = join(subdirPath, file);
              const goFile = await this.parseFile(filePath);

              // Look for Handler structs (HTTP adapters)
              const handlerTypes = goFile.types.filter(
                t => t.kind === 'struct' && t.name.endsWith('Handler')
              );

              for (const handlerType of handlerTypes) {
                const handlerName = handlerType.name
                  .replace('Handler', '')
                  .toLowerCase();

                elements.push({
                  id: `adapter-${subdir}-${handlerName}`,
                  name: handlerType.name,
                  type: 'adapter',
                  filePath: goFile.path,
                  packagePath: goFile.packageName,
                  dependencies: this.extractTypeDependencies(
                    handlerType,
                    goFile
                  ),
                  implements: this.extractHandlerInterfaces(
                    handlerType,
                    goFile
                  ),
                  usedBy: [],
                  metadata: {
                    isExported: this.isExported(handlerType.name),
                    hasTests: files.some(
                      f => f === `${file.replace('.go', '_test.go')}`
                    ),
                    complexity: this.calculateTypeComplexity(handlerType),
                    kthuluTags: goFile.kthuluTags,
                  },
                });
              }
            }
          }
        }
      }
    } catch (error) {
      this.logger.error('Error analyzing adapters', error as Error);
    }

    return elements;
  }

  private async analyzeDomain(
    domainPath: string
  ): Promise<KthuluArchitectureElement[]> {
    const elements: KthuluArchitectureElement[] = [];

    try {
      const { readdir } = await import('fs/promises');
      const files = await readdir(domainPath);

      for (const file of files) {
        if (file.endsWith('.go') && !file.endsWith('_test.go')) {
          const filePath = join(domainPath, file);
          const goFile = await this.parseFile(filePath);

          // Look for domain entities (exported structs)
          const entityTypes = goFile.types.filter(
            t =>
              t.kind === 'struct' &&
              this.isExported(t.name) &&
              !t.name.endsWith('Request') &&
              !t.name.endsWith('Response')
          );

          for (const entityType of entityTypes) {
            elements.push({
              id: `entity-${entityType.name.toLowerCase()}`,
              name: entityType.name,
              type: 'entity',
              filePath: goFile.path,
              packagePath: goFile.packageName,
              dependencies: this.extractTypeDependencies(entityType, goFile),
              implements: entityType.implements || [],
              usedBy: [],
              metadata: {
                isExported: this.isExported(entityType.name),
                hasTests: files.some(
                  f => f === `${file.replace('.go', '_test.go')}`
                ),
                complexity: this.calculateTypeComplexity(entityType),
                kthuluTags: goFile.kthuluTags,
              },
            });
          }
        }
      }
    } catch (error) {
      this.logger.error('Error analyzing domain', error as Error);
    }

    return elements;
  }

  private extractPackageName(content: string): string {
    const packageMatch = content.match(/^package\s+(\w+)/m);
    return packageMatch ? packageMatch[1] : 'main';
  }

  private extractImports(content: string): GoImport[] {
    const imports: GoImport[] = [];

    // Single import
    const singleImportRegex = /import\s+"([^"]+)"/g;
    let match;
    while ((match = singleImportRegex.exec(content)) !== null) {
      imports.push({
        path: match[1],
        isLocal: match[1].startsWith('backend/'),
      });
    }

    // Multi-line imports
    const multiImportRegex = /import\s*\(\s*([\s\S]*?)\s*\)/g;
    while ((match = multiImportRegex.exec(content)) !== null) {
      const importBlock = match[1];
      const importLines = importBlock.split('\n');

      for (const line of importLines) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('//')) {
          const importMatch = trimmed.match(/(?:(\w+)\s+)?"([^"]+)"/);
          if (importMatch) {
            imports.push({
              path: importMatch[2],
              alias: importMatch[1],
              isLocal: importMatch[2].startsWith('backend/'),
            });
          }
        }
      }
    }

    return imports;
  }

  private extractTypes(content: string): GoType[] {
    const types: GoType[] = [];

    // Struct types
    const structRegex = /type\s+(\w+)\s+struct\s*\{([^}]*)\}/g;
    let match;
    while ((match = structRegex.exec(content)) !== null) {
      const name = match[1];
      const body = match[2];

      types.push({
        name,
        kind: 'struct',
        fields: this.extractStructFields(body),
      });
    }

    // Interface types
    const interfaceRegex = /type\s+(\w+)\s+interface\s*\{([^}]*)\}/g;
    while ((match = interfaceRegex.exec(content)) !== null) {
      const name = match[1];
      const body = match[2];

      types.push({
        name,
        kind: 'interface',
        methods: this.extractInterfaceMethods(body),
      });
    }

    return types;
  }

  private extractStructFields(body: string): GoField[] {
    const fields: GoField[] = [];
    const lines = body.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('//')) {
        const fieldMatch = trimmed.match(/(\w+)\s+([^`\s]+)(?:\s+`([^`]*)`)?/);
        if (fieldMatch) {
          fields.push({
            name: fieldMatch[1],
            type: fieldMatch[2],
            tags: fieldMatch[3],
          });
        }
      }
    }

    return fields;
  }

  private extractInterfaceMethods(body: string): GoMethod[] {
    const methods: GoMethod[] = [];
    const lines = body.split('\n');

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('//')) {
        const methodMatch = trimmed.match(
          /(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\)|\s+([^,\s]+))?/
        );
        if (methodMatch) {
          methods.push({
            name: methodMatch[1],
            parameters: this.parseParameters(methodMatch[2] || ''),
            returns: this.parseParameters(
              methodMatch[3] || methodMatch[4] || ''
            ),
            isExported: this.isExported(methodMatch[1]),
          });
        }
      }
    }

    return methods;
  }

  private extractFunctions(content: string): GoFunction[] {
    const functions: GoFunction[] = [];

    const funcRegex =
      /func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(([^)]*)\)(?:\s*\(([^)]*)\)|\s+([^{]+))?/g;
    let match;
    while ((match = funcRegex.exec(content)) !== null) {
      const name = match[1];
      const params = match[2] || '';
      const returns = match[3] || match[4] || '';

      functions.push({
        name,
        parameters: this.parseParameters(params),
        returns: this.parseParameters(returns),
        isExported: this.isExported(name),
        isConstructor: name.startsWith('New'),
      });
    }

    return functions;
  }

  private extractVariables(content: string): GoVariable[] {
    const variables: GoVariable[] = [];

    const varRegex = /var\s+(\w+)(?:\s+([^=\s]+))?\s*(?:=\s*([^;\n]+))?/g;
    let match;
    while ((match = varRegex.exec(content)) !== null) {
      variables.push({
        name: match[1],
        type: match[2] || 'inferred',
        value: match[3],
        isExported: this.isExported(match[1]),
      });
    }

    return variables;
  }

  private extractConstants(content: string): GoConstant[] {
    const constants: GoConstant[] = [];

    const constRegex = /const\s+(\w+)(?:\s+([^=\s]+))?\s*=\s*([^;\n]+)/g;
    let match;
    while ((match = constRegex.exec(content)) !== null) {
      constants.push({
        name: match[1],
        type: match[2] || 'inferred',
        value: match[3],
        isExported: this.isExported(match[1]),
      });
    }

    return constants;
  }

  private extractComments(content: string): GoComment[] {
    const comments: GoComment[] = [];
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const commentMatch = line.match(/^\s*(\/\/\s*(.*))/);
      if (commentMatch) {
        comments.push({
          text: commentMatch[2],
          line: i + 1,
          isDoc:
            commentMatch[1].startsWith('///') ||
            (i + 1 < lines.length &&
              lines[i + 1].match(/^\s*(func|type|var|const)/)),
        });
      }
    }

    return comments;
  }

  private extractKthuluTags(content: string): KthuluTag[] {
    const tags: KthuluTag[] = [];
    const lines = content.split('\n');

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const tagMatch = line.match(
        /\/\/\s*@kthulu:(module|extend|shadow|wrap):(\w+)/
      );
      if (tagMatch) {
        tags.push({
          type: tagMatch[1] as any,
          target: tagMatch[2],
          line: i + 1,
        });
      }
    }

    return tags;
  }

  private parseParameters(paramStr: string): GoParameter[] {
    if (!paramStr.trim()) return [];

    const params: GoParameter[] = [];
    const parts = paramStr.split(',');

    for (const part of parts) {
      const trimmed = part.trim();
      if (trimmed) {
        const paramMatch = trimmed.match(/(?:(\w+)\s+)?([^,\s]+)/);
        if (paramMatch) {
          params.push({
            name: paramMatch[1] || '',
            type: paramMatch[2],
          });
        }
      }
    }

    return params;
  }

  private isExported(name: string): boolean {
    return name.length > 0 && name[0] === name[0].toUpperCase();
  }

  private extractModuleDependencies(goFile: GoFile): string[] {
    const deps: string[] = [];

    // Extract from imports
    for (const imp of goFile.imports) {
      if (imp.isLocal) {
        deps.push(imp.path);
      }
    }

    return deps;
  }

  private extractTypeDependencies(type: GoType, goFile: GoFile): string[] {
    const deps: string[] = [];

    // Extract from field types
    if (type.fields) {
      for (const field of type.fields) {
        const typeRef = this.extractTypeReference(field.type);
        if (typeRef) deps.push(typeRef);
      }
    }

    return deps;
  }

  private extractTypeReference(typeStr: string): string | null {
    // Extract package.Type references
    const match = typeStr.match(/(\w+)\.(\w+)/);
    return match ? `${match[1]}.${match[2]}` : null;
  }

  private extractFxProvides(goFile: GoFile): string[] {
    const provides: string[] = [];

    // Look for fx.Provide calls in variable definitions
    for (const variable of goFile.variables) {
      if (variable.value?.includes('fx.Provide')) {
        const provideMatch = variable.value.match(
          /fx\.Provide\(\s*([^)]+)\s*\)/
        );
        if (provideMatch) {
          const functions = provideMatch[1].split(',').map(f => f.trim());
          provides.push(...functions);
        }
      }
    }

    return provides;
  }

  private extractFxInvokes(goFile: GoFile): string[] {
    const invokes: string[] = [];

    // Look for fx.Invoke calls in variable definitions
    for (const variable of goFile.variables) {
      if (variable.value?.includes('fx.Invoke')) {
        const invokeMatch = variable.value.match(/fx\.Invoke\(\s*([^)]+)\s*\)/);
        if (invokeMatch) {
          invokes.push(invokeMatch[1].trim());
        }
      }
    }

    return invokes;
  }

  private extractHandlerInterfaces(
    handlerType: GoType,
    goFile: GoFile
  ): string[] {
    const interfaces: string[] = [];

    // Look for RegisterRoutes method to identify as HTTP handler
    if (handlerType.methods?.some(m => m.name === 'RegisterRoutes')) {
      interfaces.push('HTTPHandler');
    }

    return interfaces;
  }

  private calculateComplexity(goFile: GoFile): number {
    let complexity = 0;

    // Add complexity based on types, functions, etc.
    complexity += goFile.types.length * 2;
    complexity += goFile.functions.length;
    complexity += goFile.imports.length * 0.5;

    return Math.round(complexity);
  }

  private calculateTypeComplexity(type: GoType): number {
    let complexity = 1;

    if (type.fields) {
      complexity += type.fields.length * 0.5;
    }

    if (type.methods) {
      complexity += type.methods.length;
    }

    return Math.round(complexity);
  }
}
