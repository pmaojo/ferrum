/** @jest-environment node */
import { exec as execCb } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const exec = promisify(execCb);

interface CLIConfig {
  commands?: Record<string, { command: string }>;
  planGraph?: string;
  validate?: string;
  [key: string]: any;
}

function createKthuluService(cli: CLIConfig, repoPath: string) {
  const run = async (cmd: string | undefined) => {
    if (!cmd) return;
    await exec(cmd, { cwd: repoPath });
  };

  return {
    async execute(operation: string) {
      const opKey = cli.commands?.[operation]
        ? operation
        : operation === 'new' && cli.commands?.init
          ? 'init'
          : undefined;
      const cmd = opKey
        ? cli.commands![opKey].command
        : cli[operation] || (operation === 'new' ? cli.init : undefined);
      await run(cmd);
    },
    async planGraph() {
      const cmd = cli.commands?.planGraph?.command || cli.planGraph;
      await run(cmd);
    },
    async validate() {
      const cmd = cli.commands?.validate?.command || cli.validate;
      await run(cmd);
    },
  };
}

describe('template smoke tests', () => {
  const templatesDir = path.join(
    __dirname,
    '..',
    '..',
    'templates',
    'semantic_gui'
  );
  const templateFiles = fs
    .readdirSync(templatesDir)
    .filter(f => f.endsWith('.json'));

  for (const file of templateFiles) {
    const templateId = file.replace(/\.json$/, '');
    const repoPath = path.join(__dirname, '../scripts/demo-repos', templateId);

    const testFn = fs.existsSync(repoPath) ? test : test.skip;

    testFn(`${templateId} CLI commands execute`, async () => {
      const template = JSON.parse(
        await fs.promises.readFile(path.join(templatesDir, file), 'utf-8')
      );
      const service = createKthuluService(template.cli || {}, repoPath);
      await service.execute('new');
      await service.planGraph();
      await service.validate();
    });
  }
});
