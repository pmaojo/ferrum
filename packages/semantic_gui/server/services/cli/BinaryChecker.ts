import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface BinaryInfo {
  name: string;
  version?: string;
  installUrl?: string;
  installCommand?: string;
  checkCommand?: string;
  required?: boolean;
}

export interface BinaryCheckResult {
  available: boolean;
  version?: string;
  error?: string;
  installInstructions?: string;
}

export class BinaryChecker {
  /**
   * Check if a binary is available and get its version
   */
  static async checkBinary(binary: BinaryInfo): Promise<BinaryCheckResult> {
    try {
      const checkCmd = binary.checkCommand || `which ${binary.name}`;
      const { stdout, stderr } = await execAsync(checkCmd, { timeout: 5000 });

      if (stderr && stderr.includes('not found')) {
        return {
          available: false,
          error: `Binary '${binary.name}' not found`,
          installInstructions: this.getInstallInstructions(binary),
        };
      }

      // Try to extract version if possible
      let version: string | undefined;
      if (binary.checkCommand?.includes('version')) {
        version = this.extractVersion(stdout);
      }

      return {
        available: true,
        version,
      };
    } catch (error) {
      return {
        available: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        installInstructions: this.getInstallInstructions(binary),
      };
    }
  }

  /**
   * Check multiple binaries and return their status
   */
  static async checkMultipleBinaries(
    binaries: BinaryInfo[]
  ): Promise<Record<string, BinaryCheckResult>> {
    const results: Record<string, BinaryCheckResult> = {};

    for (const binary of binaries) {
      results[binary.name] = await this.checkBinary(binary);
    }

    return results;
  }

  /**
   * Check if all required binaries are available
   */
  static async checkRequiredBinaries(binaries: BinaryInfo[]): Promise<{
    allAvailable: boolean;
    missing: string[];
    results: Record<string, BinaryCheckResult>;
  }> {
    const results = await this.checkMultipleBinaries(binaries);
    const missing: string[] = [];

    for (const binary of binaries) {
      if (binary.required !== false && !results[binary.name].available) {
        missing.push(binary.name);
      }
    }

    return {
      allAvailable: missing.length === 0,
      missing,
      results,
    };
  }

  private static getInstallInstructions(binary: BinaryInfo): string {
    if (binary.installCommand) {
      return `Install with: ${binary.installCommand}`;
    }
    if (binary.installUrl) {
      return `Install from: ${binary.installUrl}`;
    }
    return `Please install '${binary.name}' to use this template`;
  }

  private static extractVersion(output: string): string | undefined {
    // Common version patterns
    const patterns = [
      /version\s+(\d+\.\d+\.\d+)/i,
      /v(\d+\.\d+\.\d+)/i,
      /(\d+\.\d+\.\d+)/,
    ];

    for (const pattern of patterns) {
      const match = output.match(pattern);
      if (match) {
        return match[1];
      }
    }

    return undefined;
  }

  /**
   * Parse CLI configuration from template and extract binary information
   */
  static parseCLIConfig(cliConfig: any): {
    mainBinary: BinaryInfo;
    dependencies: BinaryInfo[];
  } {
    // Handle templates that don't require specific binaries
    if (cliConfig.requiresBinary === false || cliConfig.binary === 'shell') {
      const mainBinary: BinaryInfo = {
        name: 'shell',
        required: false,
        checkCommand: 'echo "Shell available"',
      };
      return { mainBinary, dependencies: [] };
    }

    const mainBinary: BinaryInfo = {
      name: cliConfig.binary || 'unknown',
      version: cliConfig.version,
      installUrl: cliConfig.installUrl,
      installCommand: cliConfig.installCommand,
      checkCommand: cliConfig.checkCommand,
      required: cliConfig.required !== false,
    };

    const dependencies: BinaryInfo[] = (cliConfig.dependencies || []).map(
      (dep: any) => ({
        name: dep.name,
        version: dep.version,
        installUrl: dep.installUrl,
        installCommand: dep.installCommand,
        checkCommand: dep.checkCommand,
        required: dep.required !== false,
      })
    );

    return { mainBinary, dependencies };
  }
}
