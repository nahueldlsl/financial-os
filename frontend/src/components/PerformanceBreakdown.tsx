import { useMemo } from 'react';
import {
    TrendingUp,
    TrendingDown,
    DollarSign,
    BarChart3,
    Target,
    Activity,
    Wallet,
    ArrowUpRight,
    ArrowDownRight,
    Minus
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import type { PerformanceBreakdownData } from '../types';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// ─────────────────────────────────────────────────────
//  Format helpers
// ─────────────────────────────────────────────────────

function formatCurrency(value: number): string {
    const abs = Math.abs(value);
    const formatted = abs.toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    if (value < 0) return `-$${formatted}`;
    if (value > 0) return `+$${formatted}`;
    return `$${formatted}`;
}

function formatCurrencyNeutral(value: number): string {
    return `$${Math.abs(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

function formatPct(value: number | null): string {
    if (value === null || value === undefined) return 'N/A';
    const sign = value > 0 ? '+' : '';
    return `${sign}${value.toFixed(2)}%`;
}

function formatPE(value: number | null): string {
    if (value === null || value === undefined || value === 0) return 'N/A';
    return `${value.toFixed(1)}x`;
}

// ─────────────────────────────────────────────────────
//  Row Components
// ─────────────────────────────────────────────────────

interface MetricRowProps {
    label: string;
    value: string;
    subValue?: string;
    valueColor?: 'positive' | 'negative' | 'neutral' | 'muted';
    icon?: React.ReactNode;
    highlight?: boolean;
}

function MetricRow({ label, value, subValue, valueColor = 'neutral', icon, highlight = false }: MetricRowProps) {
    const colorClass = useMemo(() => {
        switch (valueColor) {
            case 'positive': return 'text-emerald-400';
            case 'negative': return 'text-red-400';
            case 'muted': return 'text-slate-500';
            default: return 'text-slate-100';
        }
    }, [valueColor]);

    return (
        <div className={cn(
            "group flex items-center justify-between px-5 py-3 rounded-xl transition-all duration-200",
            highlight
                ? "bg-slate-800/60 border border-slate-700/50"
                : "hover:bg-slate-800/30"
        )}>
            <div className="flex items-center gap-3">
                {icon && (
                    <div className={cn(
                        "w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors",
                        valueColor === 'positive' ? "bg-emerald-500/10 text-emerald-400" :
                        valueColor === 'negative' ? "bg-red-500/10 text-red-400" :
                        "bg-slate-700/50 text-slate-400"
                    )}>
                        {icon}
                    </div>
                )}
                <span className="text-sm text-slate-400 font-medium">{label}</span>
            </div>
            <div className="flex items-center gap-3 text-right">
                <span className={cn("font-bold text-base tabular-nums tracking-tight", colorClass)}>
                    {value}
                </span>
                {subValue && (
                    <span className={cn(
                        "text-xs font-semibold px-2 py-0.5 rounded-md tabular-nums",
                        valueColor === 'positive' ? "bg-emerald-500/10 text-emerald-400" :
                        valueColor === 'negative' ? "bg-red-500/10 text-red-400" :
                        "bg-slate-700/50 text-slate-400"
                    )}>
                        {subValue}
                    </span>
                )}
            </div>
        </div>
    );
}

function SectionDivider({ label }: { label: string }) {
    return (
        <div className="flex items-center gap-3 px-5 pt-5 pb-2">
            <div className="h-px flex-1 bg-gradient-to-r from-slate-700/80 to-transparent" />
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                {label}
            </span>
            <div className="h-px flex-1 bg-gradient-to-l from-slate-700/80 to-transparent" />
        </div>
    );
}

// ─────────────────────────────────────────────────────
//  Main Component
// ─────────────────────────────────────────────────────

interface Props {
    data: PerformanceBreakdownData | null;
    loading?: boolean;
}

export default function PerformanceBreakdown({ data, loading = false }: Props) {
    if (loading) {
        return (
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6">
                <div className="h-6 w-56 bg-slate-800 rounded-lg animate-pulse mb-6" />
                <div className="space-y-3">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <div key={i} className="flex justify-between items-center px-5 py-3">
                            <div className="h-4 w-32 bg-slate-800 rounded animate-pulse" />
                            <div className="h-4 w-24 bg-slate-800 rounded animate-pulse" />
                        </div>
                    ))}
                </div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-8 flex flex-col items-center justify-center text-center gap-3">
                <BarChart3 className="text-slate-600" size={32} />
                <p className="text-slate-500 text-sm">Sin datos de rendimiento disponibles.</p>
            </div>
        );
    }

    const gainColor = (val: number): 'positive' | 'negative' | 'neutral' =>
        val > 0 ? 'positive' : val < 0 ? 'negative' : 'neutral';

    // Bottom line icon
    const totalReturnIcon = data.total_return.value >= 0
        ? <TrendingUp size={16} />
        : <TrendingDown size={16} />;

    return (
        <div className="col-span-1 md:col-span-4 bg-slate-900/50 border border-slate-800/50 rounded-3xl py-6 overflow-hidden">
            {/* Header */}
            <div className="px-6 pb-4 flex items-center justify-between border-b border-slate-800/50">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-500/20 to-indigo-500/20 flex items-center justify-center">
                        <BarChart3 className="text-violet-400" size={20} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white tracking-tight">Performance Breakdown</h3>
                        <p className="text-xs text-slate-500">Desglose profesional de rendimiento</p>
                    </div>
                </div>
                {data.total_return.value !== 0 && (
                    <div className={cn(
                        "flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-bold",
                        data.total_return.value >= 0
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-red-500/10 text-red-400"
                    )}>
                        {data.total_return.value >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                        {formatPct(data.total_return.percentage)}
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="pt-2 space-y-0">

                {/* ─── CAPITAL ─── */}
                <SectionDivider label="Capital" />
                <MetricRow
                    label="Invested Capital"
                    value={formatCurrencyNeutral(data.invested_capital)}
                    icon={<Wallet size={16} />}
                />
                <MetricRow
                    label="Market Value"
                    value={formatCurrencyNeutral(data.market_value)}
                    icon={<DollarSign size={16} />}
                />

                {/* ─── PERFORMANCE ─── */}
                <SectionDivider label="Performance" />
                <MetricRow
                    label="Price Gain (Unrealized)"
                    value={formatCurrency(data.unrealized_gain.value)}
                    subValue={formatPct(data.unrealized_gain.percentage)}
                    valueColor={gainColor(data.unrealized_gain.value)}
                    icon={data.unrealized_gain.value >= 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                />
                <MetricRow
                    label="Dividends"
                    value={formatCurrency(data.dividends.value)}
                    subValue={data.dividends.value > 0 ? formatPct(data.dividends.percentage) : undefined}
                    valueColor={data.dividends.value > 0 ? 'positive' : 'muted'}
                    icon={<DollarSign size={16} />}
                />
                <MetricRow
                    label="Realized Gain"
                    value={formatCurrency(data.realized_gain.value)}
                    subValue={data.realized_gain.value !== 0 ? formatPct(data.realized_gain.percentage) : undefined}
                    valueColor={gainColor(data.realized_gain.value)}
                    icon={<Target size={16} />}
                />

                {/* ─── COSTS ─── */}
                <SectionDivider label="Costs" />
                <MetricRow
                    label="Transaction Costs"
                    value={data.total_costs.transaction_costs > 0 ? `-$${data.total_costs.transaction_costs.toFixed(2)}` : '$0.00'}
                    valueColor={data.total_costs.transaction_costs > 0 ? 'negative' : 'muted'}
                    icon={<Minus size={16} />}
                />

                {/* ─── BOTTOM LINE ─── */}
                <SectionDivider label="Bottom Line" />
                <MetricRow
                    label="Total Return"
                    value={formatCurrency(data.total_return.value)}
                    subValue={formatPct(data.total_return.percentage)}
                    valueColor={gainColor(data.total_return.value)}
                    icon={totalReturnIcon}
                    highlight
                />
                <MetricRow
                    label="IRR (Money-Weighted)"
                    value={data.irr_annual !== null ? `${data.irr_annual.toFixed(2)}%` : 'N/A'}
                    valueColor={data.irr_annual !== null ? gainColor(data.irr_annual) : 'muted'}
                    icon={<Activity size={16} />}
                />
                <MetricRow
                    label="TWR (Time-Weighted)"
                    value={data.twr.portfolio !== null ? formatPct(data.twr.portfolio) : 'N/A'}
                    valueColor={data.twr.portfolio !== null ? gainColor(data.twr.portfolio) : 'muted'}
                    icon={<BarChart3 size={16} />}
                />
                <MetricRow
                    label="TWR S&P 500"
                    value={data.twr.sp500 !== null ? formatPct(data.twr.sp500) : 'N/A'}
                    valueColor="neutral"
                    icon={<TrendingUp size={16} />}
                />
                {data.alpha !== null && (
                    <MetricRow
                        label="Alpha (vs S&P 500)"
                        value={formatPct(data.alpha)}
                        valueColor={gainColor(data.alpha)}
                        icon={<ArrowUpRight size={16} />}
                    />
                )}
                <MetricRow
                    label="Portfolio P/E"
                    value={formatPE(data.portfolio_pe)}
                    valueColor="neutral"
                    icon={<Target size={16} />}
                />
            </div>
        </div>
    );
}
