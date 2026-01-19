import db from './db';

// ... imports
export interface Forecast {
  id: number;
  location_id: string;
  model_name: string;
  init_time: string;
  observed_mtd: number;
  forecast_remainder: number;
  total_proj: number;
  is_partial: number; // 0 or 1
  created_at: string;
}

export interface Market {
  ticker: string;
  location_id: string;
  title: string;
  yes_price: number;
  no_price: number;
  status: string;
}

export interface StationForecast {
  location_id: string;
  models: Forecast[];
  climatology: number;
  markets: Market[]; // Added field
}

export function getLatestForecasts(): StationForecast[] {
  if (!db) return [];

  const currentMonth = new Date().getMonth() + 1; // 1-12

  const stmt = db.prepare(`
    SELECT f.* 
    FROM forecasts f
    INNER JOIN (
        SELECT location_id, model_name, MAX(init_time) as max_time
        FROM forecasts
        GROUP BY location_id, model_name
    ) latest ON f.location_id = latest.location_id 
            AND f.model_name = latest.model_name 
            AND f.init_time = latest.max_time
    ORDER BY f.location_id, f.model_name
  `);

  const rows = stmt.all() as Forecast[];

  // Fetch climatology
  const climStmt = db.prepare(`
    SELECT location_id, value FROM climatology WHERE month = ?
  `);
  const climRows = climStmt.all(currentMonth) as { location_id: string, value: number }[];
  const climMap: Record<string, number> = {};
  climRows.forEach(r => climMap[r.location_id] = r.value);

  // Fetch Markets
  // Catch error if table doesn't exist yet (in case migration didn't run via python yet)
  let marketRows: Market[] = [];
  try {
    const marketStmt = db.prepare(`
        SELECT * FROM kalshi_markets WHERE status = 'active'
      `);
    marketRows = marketStmt.all() as Market[];
  } catch (e) {
    console.error("Failed to fetch markets (table might be missing):", e);
  }

  const marketsMap: Record<string, Market[]> = {};
  marketRows.forEach(m => {
    if (!marketsMap[m.location_id]) marketsMap[m.location_id] = [];
    marketsMap[m.location_id].push(m);
  });

  // Group by location
  const grouped: Record<string, Forecast[]> = {};

  rows.forEach(row => {
    if (!grouped[row.location_id]) {
      grouped[row.location_id] = [];
    }
    grouped[row.location_id].push(row);
  });

  // Convert to array
  return Object.keys(grouped).map(locId => ({
    location_id: locId,
    models: grouped[locId],
    climatology: climMap[locId] || 3.0,
    markets: marketsMap[locId] || []
  }));
}
