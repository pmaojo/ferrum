import {
  graphNodes,
  graphEdges,
  projects,
  templates,
  validationResults,
} from '@shared/schema';
import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';

import { env } from './config';

if (!env.DATABASE_URL) {
  throw new Error(
    'DATABASE_URL must be set. Did you forget to provision a database?'
  );
}

const schema = {
  graphNodes,
  graphEdges,
  projects,
  templates,
  validationResults,
};

export const pool = new Pool({ connectionString: env.DATABASE_URL });
export const db = drizzle(pool, { schema });

// Export schema tables for use in routes
export { graphNodes, graphEdges, projects, templates, validationResults };
