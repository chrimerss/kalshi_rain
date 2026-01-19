import { getLatestForecasts } from '@/lib/api';
import { RainBucket } from '@/components/RainBucket';

// Mapping for display names
const STATION_NAMES: Record<string, string> = {
  "KNYC": "NYC (Central Park)",
  "KLOX": "Los Angeles (KLOX)",
  "KMIA": "Miami",
  "KMDW": "Chicago",
  "KSFO": "San Francisco",
  "KIAH": "Houston",
  "KSEA": "Seattle",
  "KAUS": "Austin",
  "KDFW": "Dallas",
  "KDEN": "Denver"
};

const MODEL_DURATIONS: Record<string, number> = {
  "NBM": 25,     // NBM Hourly Text usually ~25h
  "NWS": 168,    // NWS Gridpoints usually 7 days
  "ECMWF": 384,  // Open-Meteo provides up to 16 days
  "GFS": 384,
  "ICON": 384,
  "GEM": 384
};

export const dynamic = 'force-dynamic';

export default function Dashboard() {
  const stationForecasts = getLatestForecasts();

  // Sort stations to match config order? Or alphabetical?
  // Let's keep DB order or sort by name.

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800">RainCheck Forecast Dashboard</h1>
        <p className="text-gray-600">Monthly Precipitation Tracker (Inches)</p>
      </header>

      <div className="grid grid-cols-1 gap-8">
        {stationForecasts.map((sf) => {
          const locationName = STATION_NAMES[sf.location_id] || sf.location_id;

          // Get unique models
          // Filter out pure NWS_CLI and removed models (HRRR, NAM)
          const modelForecasts = sf.models.filter(m =>
            m.model_name !== 'NWS_CLI' &&
            m.model_name !== 'HRRR' &&
            m.model_name !== 'NAM'
          );
          const obsRow = sf.models.find(m => m.model_name === 'NWS_CLI');
          const currentObs = obsRow ? obsRow.observed_mtd : (modelForecasts[0]?.observed_mtd || 0);

          return (
            <div key={sf.location_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-2xl font-bold text-gray-800">{locationName}</h2>
                <div className="text-sm font-mono bg-blue-50 text-blue-800 px-3 py-1 rounded-full">
                  Observed: {currentObs.toFixed(2)}"
                </div>
              </div>

              <div className="flex flex-wrap gap-8 items-start">
                <div className="flex flex-wrap gap-4">
                  {/* Render a bucket for each model */}
                  {modelForecasts.length > 0 ? (
                    modelForecasts.map(model => {
                      let validThruText = "Month End";

                      if (model.is_partial === 1 && model.init_time) {
                        const duration = MODEL_DURATIONS[model.model_name] || 0;
                        if (duration > 0) {
                          const initDate = new Date(model.init_time);
                          // Calculate end date based on duration
                          const validDate = new Date(initDate.getTime() + duration * 3600 * 1000);
                          validThruText = validDate.toLocaleString('en-US', {
                            month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
                          });
                        }
                      }

                      // Recalculate total based on the unified currentObs to ensure consistency
                      const displayTotal = currentObs + (model.forecast_remainder || 0);

                      return (
                        <div key={model.model_name} className="w-32">
                          <RainBucket
                            locationName={locationName}
                            modelName={model.model_name}
                            observed={currentObs}
                            forecast={model.forecast_remainder}
                            total={displayTotal}
                            initTime={model.init_time}
                            climatology={sf.climatology}
                            validThruText={validThruText}
                          />
                        </div>
                      );
                    })
                  ) : (
                    <div className="text-gray-400 italic">No model forecasts available.</div>
                  )}
                </div>

                {/* Kalshi Markets */}
                {sf.markets.length > 0 && (
                  <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 min-w-[300px]">
                    <h3 className="text-xs font-bold text-slate-500 mb-3 uppercase tracking-wider flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                      Kalshi Market (Live)
                    </h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-slate-400 border-b border-slate-200">
                          <th className="pb-2 font-medium">Option (&gt; Inch)</th>
                          <th className="pb-2 font-medium text-right">Price</th>
                        </tr>
                      </thead>
                      <tbody>
                        {sf.markets.sort((a, b) => a.ticker.localeCompare(b.ticker)).map(m => {
                          // Extract cleaner title if possible, e.g. "Rain > 1 inch" -> "> 1 inch"
                          // Or just show title.
                          return (
                            <tr key={m.ticker} className="border-b border-slate-100 last:border-0 hover:bg-slate-100 transition-colors">
                              <td className="py-2 text-slate-700 font-medium truncate max-w-[200px]" title={m.title}>
                                {m.title}
                              </td>
                              <td className="py-2 text-right font-mono font-bold text-slate-900 bg-slate-100 rounded px-1">
                                {m.yes_price}¢
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                    <div className="mt-2 text-right text-xs text-slate-400">
                      Updated every min
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {stationForecasts.length === 0 && (
        <div className="text-center text-gray-500 mt-20">
          No forecast data available. Please run the backend ingestion.
        </div>
      )}
    </main>
  );
}
