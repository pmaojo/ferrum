import { createHash } from 'crypto';

export function generateNodeId(type: string, filePath: string): string {
  return createHash('sha1').update(`${type}:${filePath}`).digest('hex');
}
