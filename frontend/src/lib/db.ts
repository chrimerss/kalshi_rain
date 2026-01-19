import Database from 'better-sqlite3';
import path from 'path';

// Resolve path to the database file
const DB_PATH = path.resolve(process.cwd(), '../backend/data/raincheck.db');

let db: Database.Database;

try {
  // Use a try-catch block to handle connection errors gracefully during build
  // or if the DB file is missing.
  db = new Database(DB_PATH, { readonly: true });
} catch (error) {
  console.error('Failed to open database at', DB_PATH, error);
  // Throwing error ensures the application fails fast if DB is critical
  throw error;
}

export default db;
