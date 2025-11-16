import * as path from 'path';

import type {
  Template,
  InsertGraphNode,
  InsertGraphEdge,
} from '@shared/schema';
import * as ts from 'typescript';

interface AnalysisResult {
  nodes: InsertGraphNode[];
  edges: InsertGraphEdge[];
  validationResults: ValidationResult[];
}

interface ValidationResult {
  type: 'error' | 'warning' | 'info';
  message: string;
  filePath?: string;
  severity: number;
}

interface ParsedFile {
  filePath: string;
  content: string;
  ast?: ts.SourceFile;
  normalizedPath: string;
  exports: string[];
  imports: ImportInfo[];
}

interface ImportInfo {
  importPath: string;
  resolvedPath: string;
  importedNames: string[];
  isRelative: boolean;
}

// =============================================================================
// FASE 1: PARSING Y NORMALIZACIÓN
// =============================================================================

class FileParser {
  private fileMap = new Map<string, ParsedFile>();

  constructor(private files: Express.Multer.File[]) {}

  parse(): ParsedFile[] {
    // Convertir archivos y normalizar rutas
    this.files.forEach(file => {
      const normalizedPath = this.normalizePath(file.originalname);
      const content = file.buffer.toString();

      const parsedFile: ParsedFile = {
        filePath: file.originalname,
        content,
        normalizedPath,
        exports: [],
        imports: [],
        ast: this.parseToAST(content, file.originalname),
      };

      // Extraer exports e imports usando AST
      if (parsedFile.ast) {
        parsedFile.exports = this.extractExports(parsedFile.ast);
        parsedFile.imports = this.extractImports(
          parsedFile.ast,
          normalizedPath
        );
      }

      this.fileMap.set(normalizedPath, parsedFile);
    });

    // Resolver rutas de imports
    this.resolveImportPaths();

    return Array.from(this.fileMap.values());
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
    } catch (error) {
      console.warn(`Failed to parse ${fileName}:`, error);
      return undefined;
    }
  }

  private normalizePath(filePath: string): string {
    return filePath.replace(/\\/g, '/').toLowerCase();
  }

  private extractExports(sourceFile: ts.SourceFile): string[] {
    const exports: string[] = [];

    ts.forEachChild(sourceFile, node => {
      if (ts.isExportDeclaration(node)) {
        // export { ... }
        if (node.exportClause && ts.isNamedExports(node.exportClause)) {
          node.exportClause.elements.forEach(element => {
            exports.push(element.name.text);
          });
        }
      } else if (
        ts.isFunctionDeclaration(node) ||
        ts.isClassDeclaration(node)
      ) {
        // export function/class
        if (
          node.modifiers?.some(mod => mod.kind === ts.SyntaxKind.ExportKeyword)
        ) {
          if (node.name) {
            exports.push(node.name.text);
          }
        }
      } else if (ts.isVariableStatement(node)) {
        // export const/let/var
        if (
          node.modifiers?.some(mod => mod.kind === ts.SyntaxKind.ExportKeyword)
        ) {
          node.declarationList.declarations.forEach(decl => {
            if (ts.isIdentifier(decl.name)) {
              exports.push(decl.name.text);
            }
          });
        }
      }
    });

    return exports;
  }

  private extractImports(
    sourceFile: ts.SourceFile,
    currentFilePath: string
  ): ImportInfo[] {
    const imports: ImportInfo[] = [];

    ts.forEachChild(sourceFile, node => {
      if (
        ts.isImportDeclaration(node) &&
        node.moduleSpecifier &&
        ts.isStringLiteral(node.moduleSpecifier)
      ) {
        const importPath = node.moduleSpecifier.text;
        const isRelative = importPath.startsWith('.');

        if (isRelative) {
          const importedNames: string[] = [];

          if (node.importClause) {
            // Default import
            if (node.importClause.name) {
              importedNames.push(node.importClause.name.text);
            }

            // Named imports
            if (
              node.importClause.namedBindings &&
              ts.isNamedImports(node.importClause.namedBindings)
            ) {
              node.importClause.namedBindings.elements.forEach(element => {
                importedNames.push(element.name.text);
              });
            }
          }

          imports.push({
            importPath,
            resolvedPath: '', // Se resuelve después
            importedNames,
            isRelative,
          });
        }
      }
    });

    return imports;
  }

  private resolveImportPaths(): void {
    this.fileMap.forEach(file => {
      file.imports.forEach(importInfo => {
        if (importInfo.isRelative) {
          const resolvedPath = this.resolveRelativePath(
            file.normalizedPath,
            importInfo.importPath
          );
          importInfo.resolvedPath = resolvedPath;
        }
      });
    });
  }

  private resolveRelativePath(currentPath: string, importPath: string): string {
    const currentDir = path.dirname(currentPath);
    const resolved = path
      .resolve(currentDir, importPath)
      .replace(/\\/g, '/')
      .toLowerCase();

    // Buscar archivos con extensiones comunes
    const extensions = [
      '',
      '.ts',
      '.js',
      '.tsx',
      '.jsx',
      '/index.ts',
      '/index.js',
    ];

    for (const ext of extensions) {
      const fullPath = resolved + ext;
      if (this.fileMap.has(fullPath)) {
        return fullPath;
      }
    }

    return resolved; // Fallback si no se encuentra
  }
}

// =============================================================================
// FASE 2: GENERACIÓN DE NODOS
// =============================================================================

class NodeGenerator {
  constructor(
    private parsedFiles: ParsedFile[],
    private template: Template,
    private projectId: string
  ) {}

  generate(): InsertGraphNode[] {
    const nodes: InsertGraphNode[] = [];

    this.parsedFiles.forEach(file => {
      this.template.nodeTypes.forEach(nodeType => {
        if (this.matchesPattern(file, nodeType.pattern)) {
          const node = this.createNode(file, nodeType.type);
          nodes.push(node);
        }
      });
    });

    return nodes;
  }

  private matchesPattern(file: ParsedFile, pattern: string): boolean {
    const regex = new RegExp(pattern, 'i');
    return regex.test(file.filePath) || regex.test(file.normalizedPath);
  }

  private createNode(file: ParsedFile, nodeType: string): InsertGraphNode {
    const name = this.extractNodeName(file, nodeType);
    const description = this.extractDescription(file);

    return {
      id: `node_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      name,
      type: nodeType,
      filePath: file.filePath,
      description,
      position: this.generatePosition(),
      metadata: {
        linesOfCode: file.content.split('\n').length,
        complexity: this.analyzeComplexity(file),
        dependencies: file.imports.map(imp => imp.importPath),
        exports: file.exports,
        normalizedPath: file.normalizedPath,
        confirmed: true, // Mark as confirmed since it was detected in AST analysis
        detectedAt: new Date().toISOString(),
      },
      templateId: this.template.id,
      projectId: this.projectId,
    };
  }

  private extractNodeName(file: ParsedFile, nodeType: string): string {
    // Usar AST para extraer nombres más precisos
    if (file.ast) {
      const name = this.extractNameFromAST(file.ast, nodeType);
      if (name) return name;
    }

    // Fallback a regex si no hay AST
    return this.extractNameFromContent(file.content, file.filePath);
  }

  private extractNameFromAST(
    ast: ts.SourceFile,
    nodeType: string
  ): string | null {
    let extractedName: string | null = null;

    ts.forEachChild(ast, node => {
      if (ts.isClassDeclaration(node) && node.name) {
        extractedName = node.name.text;
      } else if (ts.isFunctionDeclaration(node) && node.name) {
        if (
          node.modifiers?.some(mod => mod.kind === ts.SyntaxKind.ExportKeyword)
        ) {
          extractedName = node.name.text;
        }
      }
    });

    return extractedName;
  }

  private extractNameFromContent(content: string, filePath: string): string {
    const classMatch = content.match(/class\s+(\w+)/);
    const functionMatch = content.match(
      /export\s+(?:async\s+)?function\s+(\w+)/
    );
    const exportMatch = content.match(/export\s+(?:const|let|var)\s+(\w+)/);

    if (classMatch) return classMatch[1];
    if (functionMatch) return functionMatch[1];
    if (exportMatch) return exportMatch[1];

    const fileName = path.basename(filePath, path.extname(filePath));
    return fileName.charAt(0).toUpperCase() + fileName.slice(1);
  }

  private extractDescription(file: ParsedFile): string {
    const jsdocMatch = file.content.match(/\/\*\*\s*(.*?)\s*\*\//s);
    if (jsdocMatch) {
      return jsdocMatch[1].replace(/\s*\*\s*/g, ' ').trim();
    }

    const commentMatch = file.content.match(/\/\/\s*(.*)/);
    if (commentMatch) {
      return commentMatch[1].trim();
    }

    return '';
  }

  private analyzeComplexity(file: ParsedFile): string {
    const lines = file.content.split('\n').length;
    const cyclomaticComplexity = (
      file.content.match(/if|else|while|for|switch|case|\?/g) || []
    ).length;

    if (cyclomaticComplexity > 10 || lines > 100) return 'High';
    if (cyclomaticComplexity > 5 || lines > 50) return 'Medium';
    return 'Low';
  }

  private generatePosition(): { x: number; y: number } {
    return {
      x: Math.floor(Math.random() * 800) + 100,
      y: Math.floor(Math.random() * 600) + 100,
    };
  }
}

// =============================================================================
// FASE 3: GENERACIÓN DE CONEXIONES
// =============================================================================

class EdgeGenerator {
  constructor(
    private nodes: InsertGraphNode[],
    private parsedFiles: ParsedFile[],
    private projectId: string
  ) {}

  generate(): InsertGraphEdge[] {
    const edges: InsertGraphEdge[] = [];
    const nodeMap = new Map(
      this.nodes.map(n => [n.metadata?.normalizedPath || n.filePath, n])
    );

    this.parsedFiles.forEach(file => {
      const sourceNode = nodeMap.get(file.normalizedPath);
      if (!sourceNode) return;

      file.imports.forEach(importInfo => {
        const targetNode = nodeMap.get(importInfo.resolvedPath);
        if (targetNode && targetNode.id !== sourceNode.id) {
          const edge = this.createEdge(sourceNode, targetNode, importInfo);
          edges.push(edge);
        }
      });
    });

    return this.deduplicateEdges(edges);
  }

  private createEdge(
    sourceNode: InsertGraphNode,
    targetNode: InsertGraphNode,
    importInfo: ImportInfo
  ): InsertGraphEdge {
    return {
      id: `edge_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      sourceNodeId: sourceNode.id,
      targetNodeId: targetNode.id,
      type: 'depends',
      metadata: {
        importType: importInfo.importedNames.length > 0 ? 'named' : 'default',
        importedNames: importInfo.importedNames,
        importPath: importInfo.importPath,
      },
      projectId: this.projectId,
    };
  }

  private deduplicateEdges(edges: InsertGraphEdge[]): InsertGraphEdge[] {
    const seen = new Set<string>();
    return edges.filter(edge => {
      const key = `${edge.sourceNodeId}-${edge.targetNodeId}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
}

// =============================================================================
// FASE 4: VALIDACIÓN
// =============================================================================

class AnalysisValidator {
  constructor(
    private nodes: InsertGraphNode[],
    private edges: InsertGraphEdge[],
    private parsedFiles: ParsedFile[]
  ) {}

  validate(): ValidationResult[] {
    const results: ValidationResult[] = [];

    results.push(...this.validateNodes());
    results.push(...this.validateEdges());
    results.push(...this.validateStructure());
    results.push(...this.validateDependencies());

    return results;
  }

  private validateNodes(): ValidationResult[] {
    const results: ValidationResult[] = [];
    const nodeNames = new Set<string>();

    this.nodes.forEach(node => {
      // Verificar nombres duplicados
      if (nodeNames.has(node.name)) {
        results.push({
          type: 'warning',
          message: `Duplicate node name: ${node.name}`,
          filePath: node.filePath,
          severity: 2,
        });
      }
      nodeNames.add(node.name);

      // Verificar complejidad alta
      if (node.metadata?.complexity === 'High') {
        results.push({
          type: 'warning',
          message: `High complexity detected in ${node.name}`,
          filePath: node.filePath,
          severity: 3,
        });
      }
    });

    return results;
  }

  private validateEdges(): ValidationResult[] {
    const results: ValidationResult[] = [];
    const nodeIds = new Set(this.nodes.map(n => n.id));

    this.edges.forEach(edge => {
      if (!nodeIds.has(edge.sourceNodeId)) {
        results.push({
          type: 'error',
          message: `Edge references non-existent source node: ${edge.sourceNodeId}`,
          severity: 5,
        });
      }

      if (!nodeIds.has(edge.targetNodeId)) {
        results.push({
          type: 'error',
          message: `Edge references non-existent target node: ${edge.targetNodeId}`,
          severity: 5,
        });
      }
    });

    return results;
  }

  private validateStructure(): ValidationResult[] {
    const results: ValidationResult[] = [];

    // Detectar nodos aislados
    const connectedNodes = new Set([
      ...this.edges.map(e => e.sourceNodeId),
      ...this.edges.map(e => e.targetNodeId),
    ]);

    const isolatedNodes = this.nodes.filter(n => !connectedNodes.has(n.id));

    if (isolatedNodes.length > 0) {
      results.push({
        type: 'info',
        message: `Found ${isolatedNodes.length} isolated nodes`,
        severity: 1,
      });
    }

    return results;
  }

  private validateDependencies(): ValidationResult[] {
    const results: ValidationResult[] = [];

    // Detectar posibles dependencias circulares (simplificado)
    const adjacencyList = new Map<string, string[]>();

    this.edges.forEach(edge => {
      if (!adjacencyList.has(edge.sourceNodeId)) {
        adjacencyList.set(edge.sourceNodeId, []);
      }
      adjacencyList.get(edge.sourceNodeId)!.push(edge.targetNodeId);
    });

    // Aquí iría la lógica de detección de ciclos más completa

    return results;
  }
}

// =============================================================================
// FUNCIÓN PRINCIPAL REFACTORIZADA
// =============================================================================

export async function analyzeCodebase(
  files: Express.Multer.File[],
  template: Template,
  projectId: string
): Promise<AnalysisResult> {
  try {
    // Fase 1: Parsing
    const parser = new FileParser(files);
    const parsedFiles = parser.parse();

    // Fase 2: Generación de nodos
    const nodeGenerator = new NodeGenerator(parsedFiles, template, projectId);
    const nodes = nodeGenerator.generate();

    // Fase 3: Generación de conexiones
    const edgeGenerator = new EdgeGenerator(nodes, parsedFiles, projectId);
    const edges = edgeGenerator.generate();

    // Fase 4: Validación
    const validator = new AnalysisValidator(nodes, edges, parsedFiles);
    const validationResults = validator.validate();

    return { nodes, edges, validationResults };
  } catch (error) {
    console.error('Error analyzing codebase:', error);

    return {
      nodes: [],
      edges: [],
      validationResults: [
        {
          type: 'error',
          message: `Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
          severity: 5,
        },
      ],
    };
  }
}
