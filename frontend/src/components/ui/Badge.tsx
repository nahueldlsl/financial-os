import React from 'react';

interface Props {
    value: number;
    suffix?: string;
}

export const Badge: React.FC<Props> = ({ value, suffix = '%' }) => {
    const isPositive = value >= 0;
    return (
        <span className={`px-2 py-1 rounded text-xs font-bold ${isPositive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
            }`}>
            {isPositive && '+'}{value}{suffix}
        </span>
    );
};