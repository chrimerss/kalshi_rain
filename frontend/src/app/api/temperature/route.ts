import { NextResponse } from 'next/server';
import { getTemperatureForecasts } from '@/lib/api';

export const dynamic = 'force-dynamic';

export async function GET() {
    try {
        const data = getTemperatureForecasts();
        return NextResponse.json(data);
    } catch (error) {
        console.error('Failed to fetch temperature forecasts:', error);
        return NextResponse.json(
            { error: 'Failed to fetch temperature data' },
            { status: 500 }
        );
    }
}
