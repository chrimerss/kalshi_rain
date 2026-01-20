import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface RainBucketProps {
  locationName: string;
  observed: number;
  forecast: number;
  modelName: string;
  total: number;
  initTime?: string; // Add initTime prop
  climatology?: number;
  validThruText?: string;
}

export function RainBucket({
  locationName,
  observed,
  forecast,
  modelName,
  total,
  initTime,
  climatology,
  validThruText
}: RainBucketProps) {
  const maxScale = Math.max(total, climatology || 0, 5) * 1.2;

  const obsHeight = (observed / maxScale) * 100;
  const fcstHeight = (forecast / maxScale) * 100;

  // Format Init Time
  const formattedTime = initTime ? new Date(initTime).toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
  }) : '';

  return (
    <div className="flex flex-col items-center p-4 bg-white rounded-lg shadow-md border border-gray-200 w-full h-full">
      <h3 className="font-bold text-lg mb-1 min-h-[3.5rem] flex items-center justify-center text-center leading-tight break-words px-2">{modelName}</h3>
      {initTime && (
        <div className="flex flex-col items-center mb-2">
          <div className="text-[10px] text-gray-400">Init: {formattedTime}</div>
          <div className="text-[10px] text-gray-500 font-medium">Valid thru: {validThruText || 'Month End'}</div>
        </div>
      )}

      {/* Bucket Container */}
      <div className="relative w-16 h-40 bg-gray-100 rounded-b-xl border-x-2 border-b-2 border-gray-400 overflow-hidden">

        {/* Climatology Line */}
        {climatology && (
          <div
            className="absolute w-full border-t-2 border-dashed border-red-500 z-10 opacity-70"
            style={{ bottom: `${(climatology / maxScale) * 100}%` }}
            title={`Climatology: ${climatology.toFixed(2)}"`}
          />
        )}

        {/* Forecast Layer (Top) */}
        <div
          className="absolute bottom-0 w-full bg-blue-300 opacity-60 pattern-diagonal-lines"
          style={{
            height: `${obsHeight + fcstHeight}%`,
            backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 5px, rgba(255,255,255,0.5) 5px, rgba(255,255,255,0.5) 10px)'
          }}
        />

        {/* Observed Layer (Base) */}
        <div
          className="absolute bottom-0 w-full bg-blue-600 transition-all duration-500"
          style={{ height: `${obsHeight}%` }}
        />
      </div>

      <div className="mt-2 text-center">
        <div className="text-xl font-bold text-blue-900">{total.toFixed(2)}"</div>
        <div className="text-[10px] text-gray-500 flex flex-col">
          <span>Obs: {observed.toFixed(2)}</span>
          <span>Fcst: {forecast.toFixed(2)}</span>
        </div>
      </div>
    </div>
  );
}
