'use client';

import { useState, useEffect } from 'react';
import TemperatureThermometer from '@/components/TemperatureThermometer';

// Mapping for display names and station IDs
// Stations with hasDashboard=true will link to the Synoptic dashboard
const STATION_INFO: Record<string, { name: string; stationId: string; hasDashboard: boolean }> = {
    "KNYC": { name: "NYC (Central Park)", stationId: "KNYC", hasDashboard: true },
    "KLAX": { name: "Los Angeles (KLAX)", stationId: "KLAX", hasDashboard: true },
    "KMIA": { name: "Miami", stationId: "KMIA", hasDashboard: true },
    "KMDW": { name: "Chicago", stationId: "KMDW", hasDashboard: true },
    "KSFO": { name: "San Francisco", stationId: "KSFO", hasDashboard: true },
    "KSEA": { name: "Seattle", stationId: "KSEA", hasDashboard: true },
    "KAUS": { name: "Austin", stationId: "KAUS", hasDashboard: true },
    "KDEN": { name: "Denver", stationId: "KDEN", hasDashboard: true },
    "KDCA": { name: "Washington DC", stationId: "KDCA", hasDashboard: true },
    "KPHL": { name: "Philadelphia", stationId: "KPHL", hasDashboard: true },
    "KMSY": { name: "New Orleans", stationId: "KMSY", hasDashboard: true },
    "KLAS": { name: "Las Vegas", stationId: "KLAS", hasDashboard: true }
};

/**
 * Parse market title to extract temperature range.
 * Examples: "20° to 21°", "Below 20°", "Above 80°"
 */
function parseMarketRange(title: string): { min: number | null; max: number | null } {
    // Match patterns like "20° to 21°" or "20 to 21"
    const rangeMatch = title.match(/(\d+)\s*°?\s*to\s*(\d+)/i);
    if (rangeMatch) {
        return { min: parseInt(rangeMatch[1]), max: parseInt(rangeMatch[2]) };
    }
    // Match "Below X" or "Under X"
    const belowMatch = title.match(/below\s*(\d+)|under\s*(\d+)/i);
    if (belowMatch) {
        const val = parseInt(belowMatch[1] || belowMatch[2]);
        return { min: null, max: val };
    }
    // Match "Above X" or "Over X"  
    const aboveMatch = title.match(/above\s*(\d+)|over\s*(\d+)/i);
    if (aboveMatch) {
        const val = parseInt(aboveMatch[1] || aboveMatch[2]);
        return { min: val, max: null };
    }
    return { min: null, max: null };
}

/**
 * Count how many forecasts fall into a market bracket.
 */
function countModelsInBracket(
    forecasts: { temp: number }[],
    range: { min: number | null; max: number | null }
): number {
    return forecasts.filter(f => {
        const temp = Math.round(f.temp);
        if (range.min !== null && range.max !== null) {
            // Range like "20° to 21°" means temp >= 20 and temp <= 21
            return temp >= range.min && temp <= range.max;
        } else if (range.min !== null) {
            // "Above X" means temp > X
            return temp > range.min;
        } else if (range.max !== null) {
            // "Below X" means temp < X
            return temp < range.max;
        }
        return false;
    }).length;
}

interface TemperatureForecast {
    location_id: string;
    target_date: string;
    model_name: string;
    forecast_type: 'high' | 'low';
    forecast_value: number;
    observed_value: number | null;
    error: number | null;
}

interface Market {
    ticker: string;
    location_id: string;
    title: string;
    yes_price: number;
    target_date?: string;
}

interface StationData {
    location_id: string;
    forecasts: TemperatureForecast[];
    markets: Market[];
}

export default function TemperaturePage() {
    const [viewType, setViewType] = useState<'high' | 'low'>('high');
    const [stationData, setStationData] = useState<StationData[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Use relative path that works with Nginx proxy at /forecast
        fetch('/forecast/api/temperature')
            .then(res => res.json())
            .then(data => {
                setStationData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error('Failed to fetch temperature data:', err);
                setLoading(false);
            });
    }, []);

    // Determine if showing today or tomorrow based on MST time
    const now = new Date();
    const mstTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/Denver' }));
    const hourMST = mstTime.getHours();
    const dayLabel = hourMST >= 20 ? 'Tomorrow' : 'Today';  // Switch at 8 PM MST
    
    const headerText = viewType === 'high' 
        ? `${dayLabel}'s Maximum Temperature (F)` 
        : `${dayLabel}'s Minimum Temperature (F)`;

    return (
        <main className="min-h-screen bg-gray-50 p-8">
            <header className="mb-8 flex flex-col md:flex-row justify-between items-end gap-4 border-b border-gray-200 pb-6">
                <div>
                    <h1 className="text-3xl font-bold text-gray-800">Temperature Forecast</h1>
                    <p className="text-gray-600 mt-1">{headerText}</p>
                </div>

                <div className="flex items-center gap-4">
                    {/* High/Low Toggle */}
                    <div className="flex items-center bg-white rounded-lg border border-gray-200 p-1">
                        <button
                            onClick={() => setViewType('high')}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                                viewType === 'high'
                                    ? 'bg-red-500 text-white shadow-sm'
                                    : 'text-gray-600 hover:bg-gray-100'
                            }`}
                        >
                            High Temp
                        </button>
                        <button
                            onClick={() => setViewType('low')}
                            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                                viewType === 'low'
                                    ? 'bg-blue-500 text-white shadow-sm'
                                    : 'text-gray-600 hover:bg-gray-100'
                            }`}
                        >
                            Low Temp
                        </button>
                    </div>

                    {/* Navigation */}
                    <nav className="flex gap-2">
                        <a href="/forecast/" className="px-4 py-2 bg-white text-slate-600 border border-gray-200 rounded-lg font-medium hover:bg-gray-50 transition">
                            Rain Forecast
                        </a>
                        <a href="/forecast/temperature" className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium shadow-sm hover:bg-blue-700 transition">
                            Temperature
                        </a>
                    </nav>
                </div>
            </header>

            {loading ? (
                <div className="text-center text-gray-500 mt-20">Loading temperature data...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {stationData.map((data) => {
                        const stationInfo = STATION_INFO[data.location_id] || { name: data.location_id, stationId: data.location_id, hasDashboard: false };
                        const locationName = stationInfo.name;
                        // Link to Synoptic dashboard with station parameter
                        const dashboardUrl = stationInfo.hasDashboard ? `/obs/?station=${data.location_id}` : null;

                        // Filter forecasts by type
                        const typeForecasts = data.forecasts.filter(f => f.forecast_type === viewType);
                        
                        // Determine target date based on MST time:
                        // Before 8 PM MST: show today's forecast
                        // After 8 PM MST: show tomorrow's forecast
                        const now = new Date();
                        // Convert to MST (UTC-7, but handle daylight saving with America/Denver)
                        const mstTime = new Date(now.toLocaleString('en-US', { timeZone: 'America/Denver' }));
                        const hourMST = mstTime.getHours();
                        
                        const dates = Array.from(new Set(typeForecasts.map(f => f.target_date))).sort();
                        const todayStr = new Date().toISOString().slice(0, 10);
                        
                        let targetDate: string;
                        if (hourMST >= 20) {
                            // After 8 PM MST: show tomorrow's forecast
                            const futureDates = dates.filter(d => d > todayStr);
                            targetDate = futureDates[0] || dates[dates.length - 1];
                        } else {
                            // Before 8 PM MST: show today's forecast
                            const todayOrFuture = dates.filter(d => d >= todayStr);
                            targetDate = todayOrFuture[0] || dates[dates.length - 1];
                        }

                        if (!targetDate) return null;

                        const relevantForecasts = typeForecasts.filter(f => f.target_date === targetDate);

                        // Build correctness counts per model using observed values (for this forecast type)
                        const modelCorrectness: Record<string, number> = {};
                        typeForecasts.forEach(f => {
                            if (f.error === null || f.error === undefined) return;
                            if (f.error === 0) {
                                modelCorrectness[f.model_name] = (modelCorrectness[f.model_name] || 0) + 1;
                            }
                        });

                        // Map to thermometer format
                        const thermoForecasts = relevantForecasts.map(f => ({
                            model: f.model_name,
                            temp: f.forecast_value,
                            correctCount: modelCorrectness[f.model_name] || 0
                        }));

                        // Only show observed for past dates (target date's observation won't exist
                        // until after 6 PM MST on that day)
                        const observed = targetDate < todayStr
                            ? typeForecasts.find(f => f.target_date === targetDate && f.observed_value !== null)?.observed_value ?? undefined
                            : undefined;

                        // Filter Markets for Target Date and temp type
                        // High temp: KXHIGH prefix, Low temp: KXLOWT prefix
                        const marketPrefix = viewType === 'high' ? 'KXHIGH' : 'KXLOWT';
                        const relevantMarkets = data.markets.filter(m => {
                            if (!m.ticker.startsWith(marketPrefix)) return false;
                            if (m.target_date) {
                                return m.target_date === targetDate;
                            }
                            return false;
                        });

                        return (
                            <div key={data.location_id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
                                <div className="flex justify-between items-center mb-4">
                                    <h2 className="text-xl font-bold text-gray-800">
                                        {dashboardUrl ? (
                                            <a 
                                                href={dashboardUrl}
                                                className="hover:text-blue-600 hover:underline transition"
                                            >
                                                {locationName}
                                            </a>
                                        ) : (
                                            locationName
                                        )}
                                    </h2>
                                    <div className="text-xs font-mono text-gray-400">
                                        {targetDate}
                                    </div>
                                </div>

                                <div className="flex flex-col gap-6">
                                    {thermoForecasts.length > 0 ? (
                                        <TemperatureThermometer
                                            forecasts={thermoForecasts}
                                            observed={observed}
                                            tempType={viewType}
                                        />
                                    ) : (
                                        <div className="text-center text-gray-400 italic py-8">
                                            No {viewType} temp forecasts available
                                        </div>
                                    )}

                                    {/* Kalshi Markets */}
                                    <div className="w-full flex flex-col gap-2">
                                        <h3 className="text-sm font-semibold text-gray-500 mb-2 border-b border-gray-100 pb-1">
                                            Kalshi {viewType === 'high' ? 'High' : 'Low'} Temp Markets
                                        </h3>
                                        {relevantMarkets.length > 0 ? (
                                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                {relevantMarkets.sort((a, b) => a.ticker.localeCompare(b.ticker)).map(m => {
                                                    const range = parseMarketRange(m.title);
                                                    const modelsInBracket = countModelsInBracket(thermoForecasts, range);
                                                    const totalModels = thermoForecasts.length;
                                                    
                                                    return (
                                                        <div key={m.ticker} className="flex justify-between items-center bg-slate-50 p-2 rounded text-sm hover:bg-slate-100">
                                                            <span className="text-slate-700" title={m.title}>
                                                                {m.title} 
                                                                <span className="text-slate-500 ml-1">
                                                                    ({modelsInBracket}/{totalModels})
                                                                </span>
                                                            </span>
                                                            <span className="font-mono font-bold text-slate-900 ml-2">{m.yes_price}¢</span>
                                                        </div>
                                                    );
                                                })}
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
            )}

            {!loading && stationData.length === 0 && (
                <div className="text-center text-gray-500 mt-20">
                    No temperature forecast data available. Please run the backend ingestion.
                </div>
            )}
        </main>
    );
}
