import { pool } from '../server/db';
import { storage } from '../server/storage';

async function main() {
  try {
    await storage.init();
    console.log('Database seeding completed');
  } catch (err) {
    console.error('Failed to seed database', err);
    process.exitCode = 1;
  } finally {
    await pool.end();
  }
}

await main();
