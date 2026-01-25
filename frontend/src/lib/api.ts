import { getDb } from './db';

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
  target_date?: string;
}

export interface StationForecast {
  location_id: string;
  models: Forecast[];
  climatology: number;
  markets: Market[]; // Added field
}

export interface TemperatureForecast {
  location_id: string;
  target_date: string;
  model_name: string;
  forecast_value: number;
  observed_value: number | null;
  error: number | null;
  created_at: string;
}

export interface TemperatureStationData {
  location_id: string;
  forecasts: TemperatureForecast[];
  markets: Market[];
}

export function getLatestForecasts(): StationForecast[] {
  const db = getDb();

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
    // Basic filter: Rain markets usually start with KXRAIN
    if (!m.ticker.startsWith('KXRAIN')) return;

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

  return Object.keys(grouped).map(locId => ({
    location_id: locId,
    models: grouped[locId],
    climatology: climMap[locId] || 3.0,
    markets: marketsMap[locId] || []
  }));
}

export function getTemperatureForecasts(): TemperatureStationData[] {
  const db = getDb();

  // Get Latest Temperature Forecasts (Next Day)
  // We want the latest *created* forecast for the *target_date*?
  // Actually, the unique constraint is (location, target_date, model).
  // We want to show the forecast for "Tomorrow" (relative to now) or "Next Day"?
  // The user said: "forecast the next day temperature".
  // And "On the next day... summarize the previous day forecast".
  // So the UI should probably show:
  // 1. Forecast for Tomorrow (Active)
  // 2. Verification of Yesterday? (Or just History?)
  // The user said: "show the kalshi market beside to the temperature forecast".
  // This implies showing the FUTURE forecast.
  // So we should query for target_date >= Today.
  // Let's just fetch all recent and allow frontend to filter?
  // Or just fetch the latest target_date available in DB?
  // Since we ingest "Tomorrow", the latest target_date should be tomorrow.

  // Let's get "Active" forecasts (target_date >= Current Date).
  // Or simply get the rows with the Max target_date.

  const stmt = db.prepare(`
      SELECT * FROM temperature_forecasts
      WHERE target_date >= date('now', 'localtime')
         OR observed_value IS NOT NULL
      ORDER BY location_id, model_name, target_date
  `);
  // Note: sqlite date('now') is UTC. 'localtime' depends on server.
  // Safest: distinct target_date descending.

  // Just get all for now, frontend can filter "Latest".
  // Actually, we probably want to group by Location and show the "Upcoming" forecast.

  const rows = stmt.all() as TemperatureForecast[];

  // Fetch Markets (Temperature)
  let marketRows: Market[] = [];
  try {
    const marketStmt = db.prepare(`SELECT * FROM kalshi_markets WHERE status = 'active'`);
    marketRows = marketStmt.all() as Market[];
  } catch (e) { }

  const marketsMap: Record<string, Market[]> = {};
  marketRows.forEach(m => {
    // Filter for Temp markets (KXHIGH, etc, or NOT KXRAIN)
    if (m.ticker.startsWith('KXRAIN')) return;

    if (!marketsMap[m.location_id]) marketsMap[m.location_id] = [];
    marketsMap[m.location_id].push(m);
  });

  const grouped: Record<string, TemperatureForecast[]> = {};
  rows.forEach(row => {
    if (!grouped[row.location_id]) grouped[row.location_id] = [];
    grouped[row.location_id].push(row);
  });

  // Also ensure we include locations even if only markets exist?
  // Or just use the STATIONS list (which we don't have in frontend really without hardcoding).
  // Reuse keys from grouped.

  // Merge keys from markets and forecasts
  const allLocs = new Set([...Object.keys(grouped), ...Object.keys(marketsMap)]);

  return Array.from(allLocs).map(locId => ({
    location_id: locId,
    forecasts: grouped[locId] || [],
    markets: marketsMap[locId] || []
  }));
}
