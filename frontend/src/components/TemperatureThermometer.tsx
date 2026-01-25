import React from 'react';

interface TemperatureThermometerProps {
    forecasts: {
        model: string;
        temp: number;
        correctCount: number;
    }[];
    observed?: number;
    tempType: 'high' | 'low';
}

const TemperatureThermometer: React.FC<TemperatureThermometerProps> = ({ 
    forecasts, 
    observed,
    tempType 
}) => {
    // Temperature range for display
    const MIN_TEMP = tempType === 'low' ? 0 : 20;
    const MAX_TEMP = tempType === 'low' ? 80 : 110;
    const RANGE = MAX_TEMP - MIN_TEMP;

    // Colors based on temp type
    const liquidColor = tempType === 'high' ? '#ef4444' : '#3b82f6'; // red-500 / blue-500
    const borderColor = tempType === 'high' ? '#7f1d1d' : '#1e3a5f'; // dark red / dark blue

    const getPercent = (temp: number) => {
        const clamped = Math.min(Math.max(temp, MIN_TEMP), MAX_TEMP);
        return ((clamped - MIN_TEMP) / RANGE) * 100;
    };

    return (
        <div className="w-full">
            <div className="flex flex-row justify-center gap-2 flex-wrap pb-2">
                {forecasts.map((f) => {
                    const percent = getPercent(f.temp);

                    return (
                        <div key={f.model} className="flex flex-col items-center min-w-[38px]">
                            {/* Correctness count */}
                            <div className="text-[10px] font-semibold text-emerald-600 mb-0.5">
                                +{f.correctCount}
                            </div>
                            
                            {/* Thermometer - 20% smaller */}
                            <div className="relative w-[32px] h-[112px] flex justify-center">
                                {/* The Tube (Stem) */}
                                <div 
                                    className="glass-casing absolute top-0 w-[19px] h-[80px] rounded-t-full z-10 overflow-hidden tube-shine"
                                    style={{ borderColor: borderColor }}
                                >
                                    {/* Tick marks */}
                                    <div className="absolute inset-0 z-20">
                                        {[0, 50, 100].map((tick) => (
                                            <div
                                                key={tick}
                                                className="tick major"
                                                style={{ top: `${tick}%` }}
                                            />
                                        ))}
                                    </div>
                                    
                                    {/* Liquid in Tube */}
                                    <div 
                                        className="absolute bottom-0 left-0 right-0 transition-all duration-300 ease-out w-full"
                                        style={{ 
                                            height: `${percent}%`, 
                                            backgroundColor: liquidColor 
                                        }}
                                    />
                                </div>

                                {/* The Bulb (Base) */}
                                <div 
                                    className="glass-casing absolute bottom-0 w-[32px] h-[32px] rounded-full z-20 flex items-center justify-center liquid-shine"
                                    style={{ borderColor: borderColor }}
                                >
                                    <div 
                                        className="w-[26px] h-[26px] rounded-full transition-colors duration-300"
                                        style={{ backgroundColor: liquidColor }}
                                    />
                                </div>

                                {/* Connector */}
                                <div className="absolute bottom-[28px] w-[19px] h-[8px] z-15">
                                    <div 
                                        className="w-[13px] h-full mx-auto transition-colors duration-300"
                                        style={{ backgroundColor: liquidColor }}
                                    />
                                </div>
                            </div>
                            
                            {/* Temperature value and model name */}
                            <div className="mt-0.5 text-center z-10">
                                <div className="font-bold text-slate-800 text-xs">
                                    {Math.round(f.temp)}°
                                </div>
                                <div className="text-[8px] font-mono text-slate-500 uppercase leading-tight">
                                    {f.model}
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>

            {observed !== undefined && (
                <div className="mt-2 text-center border-t border-slate-200 pt-2">
                    <span className="text-xs text-slate-500">Observed: </span>
                    <span 
                        className="font-bold text-sm"
                        style={{ color: liquidColor }}
                    >
                        {Math.round(observed)}°F
                    </span>
                </div>
            )}
        </div>
    );
};

export default TemperatureThermometer;
