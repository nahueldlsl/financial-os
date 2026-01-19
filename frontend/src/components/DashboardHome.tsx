import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    PieChart as RechartsPieChart,
    Pie,
    Cell,
    Tooltip,
    ResponsiveContainer
} from 'recharts';
import {
    Wallet,
    TrendingUp,
    Bitcoin,
    ArrowUpRight,
    ArrowDownRight,
    Activity,
    BrainCircuit,
    LayoutGrid,
    RefreshCw // Icono de carga
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { DashboardData, Asset } from '../types'; // Importamos tipos reales
import { SettingsModal } from './SettingsModal';
import { Settings } from 'lucide-react';
import { formatCurrency } from '../utils/format';

// --- Utility ---
function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// --- Icons Helper ---
const getIconForCategory = (category: string) => {
    switch (category) {
        case 'Stock': return <TrendingUp size={18} />;
        case 'Crypto': return <Bitcoin size={18} />;
        case 'Cash': return <Wallet size={18} />;
        default: return <LayoutGrid size={18} />;
    }
};

// --- Components Internos ---
const FilterButton = ({ label, active, onClick }: { label: string; active?: boolean; onClick?: () => void }) => (
    <button
        onClick={onClick}
        className={cn(
            "px-3 py-1 text-sm font-medium rounded-full transition-all duration-200",
            active
                ? "bg-blue-600 text-white shadow-md shadow-blue-500/20"
                : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
        )}
    >
        {label}
    </button>
);

const ModuleCard = ({ title, icon, colorClass }: { title: string; icon: React.ReactNode; colorClass: string }) => (
    <div className="group relative flex flex-col items-center justify-center gap-3 p-6 rounded-2xl bg-slate-800 border border-slate-700/50 hover:border-slate-600 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 overflow-hidden h-full cursor-pointer">
        <div className={cn("absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-300", colorClass)} />
        <div className={cn("p-4 rounded-xl bg-slate-900/50 ring-1 ring-white/10 group-hover:scale-110 transition-transform duration-300", colorClass.replace('bg-', 'text-'))}>
            {icon}
        </div>
        <span className="text-slate-200 font-medium tracking-wide">{title}</span>
    </div>
);

const AssetRow = ({ asset, total }: { asset: Asset; total: number }) => {
    // Evitar división por cero
    const percentage = total > 0 ? (asset.amount / total) * 100 : 0;

    return (
        <div className="flex items-center gap-4 p-3 hover:bg-slate-700/30 rounded-xl transition-colors group">
            <div className="p-2.5 rounded-lg bg-slate-800 text-slate-400 group-hover:text-blue-400 group-hover:bg-blue-500/10 transition-colors">
                {getIconForCategory(asset.category)}
            </div>
            <div className="flex-1 min-w-0">
                <div className="flex justify-between items-center mb-1">
                    <span className="font-medium text-slate-200 truncate">{asset.name}</span>
                    <span className="font-semibold text-slate-100">{formatCurrency(asset.amount)}</span>
                </div>
                <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className="h-full bg-blue-500 rounded-full transition-all duration-1000"
                            style={{ width: `${percentage}%` }}
                        />
                    </div>
                    <span className="text-xs text-slate-500 w-8 text-right">{percentage.toFixed(1)}%</span>
                </div>
            </div>
        </div>
    );
};

// Rename Pie import to avoid conflict
const TopPie = Pie;

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function DashboardHome() {
    const [timeRange, setTimeRange] = useState('1M');
    const [data, setData] = useState<DashboardData | null>(null);
    const [loading, setLoading] = useState(true);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    // --- Fetch Data ---
    useEffect(() => {
        const fetchDashboard = async () => {
            try {
                // Ensure race condition is minimized by backend fallback, but basic fetch here.
                const res = await fetch(`${BASE_URL}/api/dashboard`);
                if (res.ok) {
                    const result = await res.json();
                    setData(result);
                }
            } catch (error) {
                console.error("Error cargando dashboard:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchDashboard();
    }, []);

    const filters = ['1D', '1W', '1M', '3M', '1Y', 'ALL'];

    // --- Loading State ---
    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500 gap-3">
                <RefreshCw className="animate-spin" /> Cargando Financial OS...
            </div>
        );
    }

    // --- Datos Seguros ---
    const displayData = data || {
        net_worth: 0,
        performance: { value: 0, percentage: 0, isPositive: true },
        assets: [],
        chart_data: [{ name: 'Sin datos', value: 1, color: '#334155' }]
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-8 font-sans selection:bg-blue-500/30">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header Section: Net Worth & Filters */}
                <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6">
                    <div className="space-y-2">
                        <h2 className="text-slate-400 text-sm uppercase tracking-wider font-semibold">Net Worth Total</h2>
                        <div className="flex items-baseline gap-4">
                            <h1 className="text-5xl md:text-6xl font-bold text-white tracking-tight">
                                {formatCurrency(displayData.net_worth)}
                            </h1>
                            <div className={cn(
                                "flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-bold",
                                displayData.performance.isPositive ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                            )}>
                                {displayData.performance.isPositive ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                                <span>
                                    {formatCurrency(Math.abs(displayData.performance.value))} ({Math.abs(displayData.performance.percentage)}%)
                                </span>
                            </div>
                        </div>
                    </div>

                    <div className="flex gap-1.5 bg-slate-900 p-1.5 rounded-full border border-slate-800 items-center">
                        {filters.map(f => (
                            <FilterButton
                                key={f}
                                label={f}
                                active={timeRange === f}
                                onClick={() => setTimeRange(f)}
                            />
                        ))}
                        <button
                            onClick={() => setIsSettingsOpen(true)}
                            className="p-1 px-2 text-slate-400 hover:text-white transition-colors"
                            title="Configurar Broker"
                        >
                            <Settings size={18} />
                        </button>
                    </div>
                </header>

                <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

                {/* Bento Grid Layout */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Main Visual: Asset Distribution (Spans 2 columns) */}
                    <div className="lg:col-span-2 bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 md:p-8 flex flex-col md:flex-row gap-8 backdrop-blur-sm">

                        {/* Chart Section */}
                        <div className="flex-1 flex flex-col items-center justify-center relative min-h-[300px]">
                            <h3 className="absolute top-0 left-0 text-lg font-semibold text-slate-300 flex items-center gap-2">
                                <LayoutGrid size={20} className="text-blue-500" />
                                Asset Allocation
                            </h3>
                            <ResponsiveContainer width="100%" height={300}>
                                <RechartsPieChart>
                                    <TopPie
                                        data={displayData.chart_data}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={80}
                                        outerRadius={110}
                                        paddingAngle={5}
                                        dataKey="value"
                                        stroke="none"
                                    >
                                        {displayData.chart_data.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </TopPie>
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', borderRadius: '12px', color: '#f1f5f9' }}
                                        itemStyle={{ color: '#e2e8f0' }}
                                        formatter={(value: number | undefined) => [formatCurrency(value ?? 0), 'Valor']}
                                    />
                                </RechartsPieChart>
                            </ResponsiveContainer>
                            {/* Center Text Overlay */}
                            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                <div className="text-center">
                                    <p className="text-slate-500 text-sm font-medium">Total Assets</p>
                                    <p className="text-2xl font-bold text-white">{displayData.assets.length}</p>
                                </div>
                            </div>
                        </div>

                        {/* List Section */}
                        <div className="flex-1 overflow-y-auto max-h-[350px] pr-2 custom-scrollbar">
                            <h3 className="text-lg font-semibold text-slate-300 mb-4 sticky top-0 bg-slate-900/95 py-2 z-10">Top Assets</h3>
                            <div className="space-y-1">
                                {displayData.assets.length > 0 ? (
                                    displayData.assets.sort((a, b) => b.amount - a.amount).map(asset => (
                                        <AssetRow key={asset.id} asset={asset} total={displayData.net_worth} />
                                    ))
                                ) : (
                                    <p className="text-slate-500 text-sm text-center py-4">No hay activos registrados.</p>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Quick Actions / Modules Grid */}
                    <div className="grid grid-cols-2 gap-4 auto-rows-fr">
                        <Link to="/cash" className="block h-full">
                            <ModuleCard
                                title="Cash Flow"
                                icon={<ArrowUpRight size={24} />}
                                colorClass="bg-emerald-500"
                            />
                        </Link>
                        <Link to="/market" className="block h-full">
                            <ModuleCard
                                title="Stock Portfolio"
                                icon={<TrendingUp size={24} />}
                                colorClass="bg-blue-500"
                            />
                        </Link>

                        {/* Placeholder links for future modules */}
                        <div className="block h-full opacity-75 cursor-not-allowed">
                            <ModuleCard
                                title="Crypto (Soon)"
                                icon={<Bitcoin size={24} />}
                                colorClass="bg-amber-500"
                            />
                        </div>
                        <div className="block h-full opacity-75 cursor-not-allowed">
                            <ModuleCard
                                title="Analytics (Soon)"
                                icon={<Activity size={24} />}
                                colorClass="bg-violet-500"
                            />
                        </div>

                        <div className="col-span-2">
                            <button className="w-full h-full flex items-center justify-center gap-3 p-6 rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold transition-all shadow-lg hover:shadow-indigo-500/25 group">
                                <BrainCircuit size={28} className="group-hover:rotate-12 transition-transform" />
                                <span>Ask AI Oracle</span>
                            </button>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
