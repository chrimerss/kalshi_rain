
import { getTemperatureForecasts } from '@/lib/api';
import TemperatureThermometer from '@/components/TemperatureThermometer';

export const dynamic = 'force-dynamic';

// Mapping for display names
const STATION_NAMES: Record<string, string> = {
    "KNYC": "NYC (Central Park)",
    "KLAX": "Los Angeles (KLAX)",
    "KMIA": "Miami",
    "KMDW": "Chicago",
    "KSFO": "San Francisco",
    "KHOU": "Houston (Hobby)",
    "KSEA": "Seattle",
    "KAUS": "Austin",
    "KDFW": "Dallas",
    "KDEN": "Denver"
};

export default function TemperaturePage() {
    const stationData = getTemperatureForecasts();

    return (
        <main className="min-h-screen bg-gray-50 p-8">
            <header className="mb-8 flex flex-col md:flex-row justify-between items-end gap-4 border-b border-gray-200 pb-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-800">Temperature Forecast</h1>
                    <p className="text-gray-600 mt-1">Next Day Maximum Temperature (F)</p>
                </div>

                <nav className="flex gap-2">
                    <a href="/forecast/" className="px-4 py-2 bg-white text-slate-600 border border-gray-200 rounded-lg font-medium hover:bg-gray-50 transition">
                        Rain Forecast
                    </a>
                    <a href="/forecast/temperature" className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium shadow-sm hover:bg-blue-700 transition">
                        Temperature
                    </a>
                </nav>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {stationData.map((data) => {
                    const locationName = STATION_NAMES[data.location_id] || data.location_id;

                    // Process Forecasts
                    const dates = Array.from(new Set(data.forecasts.map(f => f.target_date))).sort();
                    const targetDate = dates[0]; // Earliest future date (Tomorrow)

                    if (!targetDate) return null;

                    const relevantForecasts = data.forecasts.filter(f => f.target_date === targetDate);

                    // Build correctness counts per model using observed values.
                    const modelCorrectness: Record<string, number> = {};
                    data.forecasts.forEach(f => {
                        if (f.observed_value === null || f.observed_value === undefined) return;
                        const roundedForecast = Math.round(f.forecast_value);
                        const roundedObserved = Math.round(f.observed_value);
                        if (roundedForecast === roundedObserved) {
                            modelCorrectness[f.model_name] = (modelCorrectness[f.model_name] || 0) + 1;
                        }
                    });

                    // Map to thermometer format
                    const thermoForecasts = relevantForecasts.map(f => {
                        let color = "bg-blue-500";
                        if (f.model_name === 'NWS') color = "bg-slate-700 border-yellow-400"; // Highlight NWS
                        else if (f.model_name.includes('ECMWF')) color = "bg-emerald-500";
                        else if (f.model_name.includes('GFS')) color = "bg-blue-600";

                        return {
                            model: f.model_name,
                            temp: f.forecast_value,
                            color: color,
                            correctCount: modelCorrectness[f.model_name] || 0
                        };
                    });

                    // Observed?
                    // We store observed_value in the same rows.
                    // But check if any row has it.
                    // Usually for Tomorrow's forecast, it's null.

                    // Filter Markets for Target Date
                    const relevantMarkets = data.markets.filter(m => {
                        if (m.target_date) {
                            return m.target_date === targetDate;
                        }
                        return false;
                    });

                    return (
                        <div key={data.location_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                            <div className="flex justify-between items-center mb-4">
                                <h2 className="text-xl font-bold text-gray-800">{locationName}</h2>
                                <div className="text-xs font-mono text-gray-400">
                                    {targetDate}
                                </div>
                            </div>

                            <div className="flex flex-col gap-6">
                                <TemperatureThermometer
                                    locationId={data.location_id}
                                    stationName={locationName}
                                    forecasts={thermoForecasts}
                                />

                                {/* Markets */}
                                <div className="w-full flex flex-col gap-2">
                                    <h3 className="text-sm font-semibold text-gray-500 mb-2 border-b border-gray-100 pb-1">Kalshi Markets</h3>
                                    {relevantMarkets.length > 0 ? (
                                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                            {relevantMarkets.sort((a, b) => a.ticker.localeCompare(b.ticker)).map(m => (
                                                <div key={m.ticker} className="flex justify-between items-center bg-slate-50 p-2 rounded text-sm hover:bg-slate-100">
                                                    <span className="truncate max-w-[150px] text-slate-700" title={m.title}>{m.title}</span>
                                                    <span className="font-mono font-bold text-slate-900">{m.yes_price}¢</span>
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <div className="text-xs text-gray-400 italic">No markets found for this date.</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </main>
    );
}
