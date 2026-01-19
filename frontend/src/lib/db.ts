import Database from 'better-sqlite3';
import path from 'path';

// Resolve path to the database file
const DB_PATH = path.resolve(process.cwd(), '../backend/data/raincheck.db');

let dbInstance: Database.Database | null = null;

export function getDb(): Database.Database {
  if (!dbInstance) {
    try {
      // Check if running in build context where DB might not exist
      // Better-sqlite3 with readonly=true throws if missing.
      // We can just try-catch.
      dbInstance = new Database(DB_PATH, { readonly: true });
    } catch (error: any) {
      // If we are building, this might be expected if we don't block SSG/SSR correctly.
      // But preventing crash is safer.
      console.error('Failed to open database at', DB_PATH, error.message);
      throw error;
    }
  }
  return dbInstance;
}
