export interface ParsedFile {
  path: string;
  content: string;
  imports: string[];
  exports: string[];
  classes: string[];
  functions: string[];
  interfaces: string[];
}

export class ASTParser {
  static parseTypeScript(filePath: string, content: string): ParsedFile {
    const result: ParsedFile = {
      path: filePath,
      content,
      imports: [],
      exports: [],
      classes: [],
      functions: [],
      interfaces: [],
    };

    // Extract imports
    const importRegex =
      /import\s+(?:(?:\{[^}]*\}|\w+|\*\s+as\s+\w+)\s+from\s+)?['"]([^'"]+)['"]/g;
    let importMatch;
    while ((importMatch = importRegex.exec(content)) !== null) {
      result.imports.push(importMatch[1]);
    }

    // Extract exports
    const exportRegex =
      /export\s+(?:default\s+)?(?:class|function|const|let|var|interface|type)\s+(\w+)/g;
    let exportMatch;
    while ((exportMatch = exportRegex.exec(content)) !== null) {
      result.exports.push(exportMatch[1]);
    }

    // Extract classes
    const classRegex = /(?:export\s+)?class\s+(\w+)/g;
    let classMatch;
    while ((classMatch = classRegex.exec(content)) !== null) {
      result.classes.push(classMatch[1]);
    }

    // Extract functions
    const functionRegex = /(?:export\s+)?(?:async\s+)?function\s+(\w+)/g;
    let functionMatch;
    while ((functionMatch = functionRegex.exec(content)) !== null) {
      result.functions.push(functionMatch[1]);
    }

    // Extract interfaces
    const interfaceRegex = /(?:export\s+)?interface\s+(\w+)/g;
    let interfaceMatch;
    while ((interfaceMatch = interfaceRegex.exec(content)) !== null) {
      result.interfaces.push(interfaceMatch[1]);
    }

    return result;
  }

  static extractDependencies(
    files: ParsedFile[]
  ): Array<{ source: string; target: string; type: string }> {
    const dependencies: Array<{
      source: string;
      target: string;
      type: string;
    }> = [];

    for (const file of files) {
      for (const importPath of file.imports) {
        // Find the target file
        const targetFile = files.find(
          (f) =>
            f.path.includes(importPath) ||
            f.path.endsWith(`${importPath}.ts`) ||
            f.path.endsWith(`${importPath}.tsx`)
        );

        if (targetFile) {
          dependencies.push({
            source: file.path,
            target: targetFile.path,
            type: 'imports',
          });
        }
      }
    }

    return dependencies;
  }

  static analyzeComplexity(content: string): {
    cyclomaticComplexity: number;
    linesOfCode: number;
    maintainabilityIndex: number;
  } {
    const lines = content.split('\n').filter((line) => line.trim().length > 0);
    const linesOfCode = lines.length;

    // Count decision points for cyclomatic complexity
    const decisionPoints = (
      content.match(/if|else if|while|for|switch|case|catch|\?|&&|\|\|/g) || []
    ).length;
    const cyclomaticComplexity = decisionPoints + 1;

    // Simple maintainability index calculation
    const halsteadVolume = content.length * Math.log2(content.length || 1);
    const maintainabilityIndex = Math.max(
      0,
      171 -
        5.2 * Math.log(halsteadVolume) -
        0.23 * cyclomaticComplexity -
        16.2 * Math.log(linesOfCode)
    );

    return {
      cyclomaticComplexity,
      linesOfCode,
      maintainabilityIndex: Math.round(maintainabilityIndex),
    };
  }
}
