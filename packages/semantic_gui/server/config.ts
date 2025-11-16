import { config as loadEnv } from 'dotenv';
import { z } from 'zod';

loadEnv();

const schema = z.object({
  GROQ_API_KEY: z.string().min(1, 'GROQ_API_KEY is required'),
  SESSION_SECRET: z.string().min(1, 'SESSION_SECRET is required'),
  DATABASE_URL: z.string().min(1, 'DATABASE_URL is required'),
  NOTION_INTEGRATION_SECRET: z.string().optional(),
  NOTION_PAGE_URL: z.string().optional(),
  NODE_ENV: z.string().optional(),
});

export type Env = z.infer<typeof schema>;

export function getEnv(env: NodeJS.ProcessEnv = process.env): Env {
  const result = schema.safeParse(env);
  if (!result.success) {
    const missing = result.error.issues.map(i => i.path.join('.')).join(', ');
    throw new Error(`Missing environment variables: ${missing}`);
  }
  return result.data;
}

export const env = getEnv();
