import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, type IChartApi, type Time } from 'lightweight-charts';
import { AreaSeries, LineStyle, type LineWidth } from 'lightweight-charts';
interface ChartData {
    time: string;
    value: number;
}

interface PriceChartProps {
    data: ChartData[];
    avgPrice?: number;
    color?: string; // Kept for API compatibility, but we might implement dynamic logic internally
}

const PriceChart: React.FC<PriceChartProps> = ({ data, avgPrice }) => {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<IChartApi | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        const handleResize = () => {
            if (chartRef.current && chartContainerRef.current) {
                chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { type: ColorType.Solid, color: 'transparent' },
                textColor: '#9ca3af',
            },
            width: chartContainerRef.current.clientWidth,
            height: 300,
            grid: {
                vertLines: { color: '#374151' },
                horzLines: { color: '#374151' },
            },
            rightPriceScale: {
                borderColor: '#374151',
            },
            timeScale: {
                borderColor: '#374151',
                timeVisible: true,
            },
        });

        chartRef.current = chart;

        const series = chart.addSeries(AreaSeries, {
            lineColor: '#10b981', // Default Green
            topColor: 'rgba(16, 185, 129, 0.4)',
            bottomColor: 'rgba(16, 185, 129, 0.0)',
            lineWidth: 2,
        });

        // Determine trend color
        if (data.length > 1) {
            const first = data[0].value;
            const last = data[data.length - 1].value;
            if (last < first) {
                series.applyOptions({
                    lineColor: '#ef4444', // Red
                    topColor: 'rgba(239, 68, 68, 0.4)',
                    bottomColor: 'rgba(239, 68, 68, 0.0)',
                });
            }
        }

        // Lightweight charts expects time as string 'YYYY-MM-DD' or object. 
        // Our backend provides strictly 'YYYY-MM-DD'.
        // We need to ensure data is sorted by time, but backend should handle this ideally. 
        // We'll trust backend for now or simple sort here just in case.
        const sortedData = [...data].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

        series.setData(sortedData.map(d => ({ time: d.time as Time, value: d.value })));

        if (avgPrice) {
            // Price Line for Average Position
            const avgPriceLine = {
                price: avgPrice,
                color: '#fbbf24',
                // SOLUCIÓN: Casteamos el número al tipo específico que pide la librería
                lineWidth: 2 as LineWidth,
                lineStyle: LineStyle.Dashed, // Usamos el Enum en vez del número "2" a secas
                axisLabelVisible: true,
                title: 'Mi Precio',
            };
            series.createPriceLine(avgPriceLine);
        }

        // Fit content
        chart.timeScale().fitContent();

        window.addEventListener('resize', handleResize);

        const resizeObserver = new ResizeObserver(() => handleResize());
        resizeObserver.observe(chartContainerRef.current);

        return () => {
            window.removeEventListener('resize', handleResize);
            resizeObserver.disconnect();
            chart.remove();
        };
    }, [data, avgPrice]);

    if (!data || data.length === 0) {
        return <div className="h-[300px] flex items-center justify-center text-gray-500 bg-gray-900/50 rounded-xl border border-gray-800">No Data Available</div>;
    }

    return (
        <div className="w-full h-[300px] bg-gray-900/50 rounded-xl p-4 border border-gray-800 flex flex-col">
            <div ref={chartContainerRef} className="w-full h-full" />
        </div>
    );
};

export default PriceChart;
