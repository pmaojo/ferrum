import { getEnv } from '../config';

describe('config', () => {
  const baseEnv = {
    GROQ_API_KEY: 'k',
    SESSION_SECRET: 's',
    DATABASE_URL: 'postgres://localhost/db',
  };

  it('returns parsed env when all vars present', () => {
    expect(getEnv(baseEnv)).toEqual(baseEnv);
  });

  it('throws when required var missing', () => {
    const env = { ...baseEnv };
    delete (env as any).GROQ_API_KEY;
    expect(() => getEnv(env)).toThrow('GROQ_API_KEY');
  });
});
