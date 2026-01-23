
import React from 'react';

interface TemperatureThermometerProps {
    locationId: string;
    stationName: string;
    forecasts: {
        model: string;
        temp: number;
        color: string;
        correctCount: number;
    }[];
    observed?: number;
}

const TemperatureThermometer: React.FC<TemperatureThermometerProps> = ({ stationName, forecasts, observed }) => {
    const MIN_TEMP = 20;
    const MAX_TEMP = 110;
    const RANGE = MAX_TEMP - MIN_TEMP;

    const getPercent = (temp: number) => {
        const clamped = Math.min(Math.max(temp, MIN_TEMP), MAX_TEMP);
        return ((clamped - MIN_TEMP) / RANGE) * 100;
    };

    return (
        <div className="w-full">
            {/* Station Name removed as requested */}

            <div className="flex flex-row justify-center gap-4 overflow-x-auto pb-2">
                {forecasts.map((f) => {
                    const percent = getPercent(f.temp);
                    const emptyPercent = 100 - percent;

                    const backgroundStyle = {
                        background: `linear-gradient(to bottom, #fff 0%, #fff ${emptyPercent}%, #db3f02 ${emptyPercent}%, #db3f02 100%)`
                    };

                    return (
                        <div key={f.model} className="flex flex-col items-center min-w-[40px]">
                            <div className="text-[11px] font-semibold text-emerald-700">
                                +{f.correctCount}
                            </div>
                            <div className="thermometer-wrapper scale-75 origin-bottom transform-gpu">
                                <span className="thermometer" style={backgroundStyle}>
                                    <span className="invisible">Temp</span>
                                </span>
                            </div>
                            <div className="mt-2 text-center z-10">
                                <div className="font-bold text-slate-800 text-sm">{f.temp.toFixed(1)}°</div>
                                <div className="text-[10px] font-mono text-slate-500 uppercase">{f.model}</div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {observed !== undefined && (
                <div className="mt-2 text-center border-t border-slate-200 pt-1">
                    <span className="text-xs text-slate-500">Observed: </span>
                    <span className="font-bold text-slate-800 text-sm">{observed.toFixed(1)}°</span>
                </div>
            )}
        </div>
    );
};

export default TemperatureThermometer;
