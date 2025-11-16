import * as fs from 'node:fs';

import { NestFactory } from '@nestjs/core';
import { SpelunkerModule } from 'nestjs-spelunker';

import { AppModule } from '../src/app.module';

async function main() {
  const app = await NestFactory.createApplicationContext(AppModule, {
    logger: false,
  });
  const tree = SpelunkerModule.explore(app);
  const root = SpelunkerModule.graph(tree);
  const edges = SpelunkerModule.findGraphEdges(root);
  fs.mkdirSync('graph', { recursive: true });
  fs.writeFileSync(
    'graph/di-graph.json',
    JSON.stringify({ tree, edges }, null, 2)
  );
  await app.close();
}
main();
