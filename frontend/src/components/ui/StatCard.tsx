import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface Props {
    title: string;
    value: string | number;
    trend?: 'up' | 'down' | 'neutral';
    icon?: React.ReactNode;
    className?: string;
}

export const StatCard: React.FC<Props> = ({ title, value, trend, icon, className = "" }) => {
    // Determinamos color basado en la tendencia
    const colorClass = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-100';

    return (
        <div className={`bg-slate-900 border border-slate-800 p-6 rounded-2xl ${className}`}>
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider">{title}</p>
            <div className={`flex items-center gap-2 mt-2 text-3xl font-bold ${colorClass}`}>
                {icon}
                {value}
            </div>
        </div>
    );
};