export interface ArchitectureCLI {
  /**
   * Generate an architecture graph based on the project's codebase
   */
  planGraph(): Promise<string>;

  /**
   * Validate the architecture using the CLI if supported
   */
  validate?(): Promise<string>;
}
