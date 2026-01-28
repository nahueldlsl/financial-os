import React from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface ChartData {
    time: string;
    price: number;
}

interface PriceChartProps {
    data: ChartData[];
    avgPrice?: number;
    color?: string;
}

const PriceChart: React.FC<PriceChartProps> = ({ data, avgPrice, color = "#3b82f6" }) => {

    if (!data || data.length === 0) {
        return <div className="h-64 flex items-center justify-center text-gray-500">No Data Available</div>;
    }

    // Calcular min/max para escalar el eje Y mejor
    const prices = data.map(d => d.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const padding = (maxPrice - minPrice) * 0.1;

    return (
        <div className="w-full h-[300px] bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data}>
                    <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                            <stop offset="95%" stopColor={color} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" vertical={false} />
                    <XAxis
                        dataKey="time"
                        hide={true}
                    />
                    <YAxis
                        domain={[minPrice - padding, maxPrice + padding]}
                        orientation="right"
                        tick={{ fill: '#9ca3af', fontSize: 12 }}
                        tickFormatter={(val) => `$${val.toFixed(2)}`}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                        itemStyle={{ color: '#f3f4f6' }}
                        formatter={(value: any) => [`$${parseFloat(value).toFixed(2)}`, 'Price']}
                        labelFormatter={(label) => new Date(label).toLocaleDateString()}
                    />
                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke={color}
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                        strokeWidth={2}
                    />

                    {avgPrice !== undefined && avgPrice > 0 && (
                        <ReferenceLine
                            y={avgPrice}
                            stroke="#10b981"
                            strokeDasharray="5 5"
                            label={{ position: 'left', value: 'Avg', fill: '#10b981', fontSize: 10 }}
                        />
                    )}
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default PriceChart;
