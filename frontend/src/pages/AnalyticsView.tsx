import { useState, useEffect, useMemo } from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Legend,
    PieChart,
    Pie,
    Cell
} from 'recharts';
import {
    Activity,
    AlertTriangle,
    ShieldAlert,
    TrendingUp,
    Info,
    ArrowLeft
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

import type { AnalyticsMetrics, ValuationResponse, ValuationAnalysis, PerformanceBreakdownData } from '../types';
import { SkeletonCard, SkeletonChart } from '../components/ui/Skeletons';
import PerformanceBreakdown from '../components/PerformanceBreakdown';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AnalyticsView() {
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState<string | null>(null);
    const [metrics, setMetrics] = useState<AnalyticsMetrics | null>(null);
    const [chartData, setChartData] = useState<any[]>([]);
    const [valuation, setValuation] = useState<ValuationResponse | null>(null);
    const [diversification, setDiversification] = useState<any>(null);
    const [perfBreakdown, setPerfBreakdown] = useState<PerformanceBreakdownData | null>(null);
    const [period, setPeriod] = useState('1y');

    const fetchAnalyticsData = async () => {
        setLoading(true);
        setFetchError(null);
        try {
            const [metricsRes, chartRes, valuationRes, divRes, perfRes] = await Promise.all([
                fetch(`${BASE_URL}/api/analytics/metrics?period=${period}`),
                fetch(`${BASE_URL}/api/analytics/portfolio-performance`),
                fetch(`${BASE_URL}/api/analytics/valuation`),
                fetch(`${BASE_URL}/api/analytics/diversification`),
                fetch(`${BASE_URL}/api/analytics/performance-breakdown`)
            ]);

            if (metricsRes.ok) setMetrics(await metricsRes.json());
            if (chartRes.ok) {
                const jsonRes = await chartRes.json();
                setChartData(jsonRes.data || jsonRes || []);
            }
            if (valuationRes.ok) setValuation(await valuationRes.json());
            if (divRes.ok) setDiversification(await divRes.json());
            if (perfRes.ok) setPerfBreakdown(await perfRes.json());
        } catch (err) {
            console.error("Error fetching analytics", err);
            setFetchError("No se pudo conectar con el servidor de analytics. Verifica tu conexión.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnalyticsData();
    }, [period]);

    const chartDataMemo = useMemo(() => {
        if (!chartData || chartData.length === 0) return [];
        
        let filteredData = chartData;
        // Period cutoff calculation
        const cutoff = new Date();
        
        if (period === '1mo') cutoff.setMonth(cutoff.getMonth() - 1);
        else if (period === '3mo') cutoff.setMonth(cutoff.getMonth() - 3);
        else if (period === '6mo') cutoff.setMonth(cutoff.getMonth() - 6);
        else if (period === '1y') cutoff.setFullYear(cutoff.getFullYear() - 1);
        else if (period === 'ytd') {
            cutoff.setMonth(0, 1);
            cutoff.setHours(0, 0, 0, 0);
        } else {
            cutoff.setFullYear(2000);
        }

        if (period !== 'max') {
            filteredData = chartData.filter((day: any) => {
                const d = new Date(day.fecha || day.date);
                return d >= cutoff;
            });
        }
        
        if (filteredData.length === 0) return [];

        const basePortPct = Number(filteredData[0].pct_portafolio || filteredData[0].portfolio_value || 0);
        const baseSp500Pct = Number(filteredData[0].pct_sp500 || filteredData[0].benchmark_value || 0);
        const basePortMulti = 1 + (basePortPct / 100);
        const baseSp500Multi = 1 + (baseSp500Pct / 100);

        // FIX-3: Guard contra dividir por ~0 cuando pct ≈ -100%
        const canRebase = Math.abs(basePortMulti) > 0.001 && Math.abs(baseSp500Multi) > 0.001;

        return filteredData.map((day: any) => {
            const rawDate = day.fecha || day.date || new Date().toISOString();
            const dateObj = new Date(rawDate);
            const formattedDate = isNaN(dateObj.getTime()) 
                ? 'Invalid' 
                : dateObj.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
                
            const port_pct = Number(day.pct_portafolio || day.portfolio_value || 0);
            const sp500_pct = Number(day.pct_sp500 || day.benchmark_value || 0);

            let adjusted_port: number;
            let adjusted_sp500: number;

            if (canRebase) {
                adjusted_port = (((1 + port_pct / 100) / basePortMulti) - 1) * 100;
                adjusted_sp500 = (((1 + sp500_pct / 100) / baseSp500Multi) - 1) * 100;
            } else {
                adjusted_port = port_pct - basePortPct;
                adjusted_sp500 = sp500_pct - baseSp500Pct;
            }

            return {
                ...day,
                formattedDate,
                pct_portafolio: Number(adjusted_port.toFixed(2)),
                pct_sp500: Number(adjusted_sp500.toFixed(2))
            };
        });
    }, [chartData, period]);

    // FIX-14: Skeleton Loading State
    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-8 font-sans">
                <div className="max-w-7xl mx-auto space-y-8">
                    <div className="h-12 w-64 bg-slate-800 rounded-xl animate-pulse" />
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        <SkeletonCard />
                        <SkeletonCard />
                        <SkeletonCard />
                        <SkeletonCard />
                        <SkeletonChart className="col-span-1 md:col-span-4 h-[450px]" />
                    </div>
                </div>
            </div>
        );
    }

    // FIX-15: Empty State para portafolio nuevo o sin datos
    if (!chartData || chartData.length <= 1) {
        return (
            <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-8 font-sans">
                <div className="max-w-2xl mx-auto text-center py-24 space-y-8">
                    <div className="mx-auto w-24 h-24 rounded-full bg-violet-500/10 flex items-center justify-center">
                        <Activity className="text-violet-500" size={40} />
                    </div>
                    <h2 className="text-3xl font-bold text-white">Tu Motor Analítico está Listo</h2>
                    <p className="text-slate-400 max-w-md mx-auto leading-relaxed">
                        Necesitamos al menos <strong className="text-white">2 días de historial</strong> con posiciones activas 
                        para calcular métricas de riesgo, volatilidad y rendimiento comparativo con el S&P 500.
                    </p>
                    <div className="flex flex-col gap-3 items-center">
                        <Link 
                            to="/market"
                            className="inline-flex items-center gap-2 px-8 py-4 bg-violet-600 hover:bg-violet-500 text-white rounded-2xl font-bold transition-all shadow-lg shadow-violet-500/25"
                        >
                            <TrendingUp size={20} />
                            Registrar Primera Inversión
                        </Link>
                        <Link to="/" className="text-slate-500 hover:text-white text-sm transition-colors">
                            ← Volver al Dashboard
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    // Default safe objects
    const safeMetrics = metrics || { annualized_volatility_pct: 0, beta: null, sharpe_ratio: 0, max_drawdown_pct: 0 };
    const isBetaHigh = safeMetrics.beta !== null && safeMetrics.beta > 1.2;
    const isDrawdownCritical = safeMetrics.max_drawdown_pct < -20;

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-8 font-sans">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* FIX-17: Error Banner */}
                {fetchError && (
                    <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3 text-red-400 text-sm">
                        <AlertTriangle size={18} />
                        <span className="flex-1">{fetchError}</span>
                        <button onClick={() => { setFetchError(null); fetchAnalyticsData(); }} className="text-white bg-red-500/20 px-3 py-1 rounded-lg hover:bg-red-500/30 transition-colors">
                            Reintentar
                        </button>
                    </div>
                )}
                
                {/* Header */}
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <Link to="/" className="p-2 bg-slate-900 hover:bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors">
                            <ArrowLeft size={24} />
                        </Link>
                        <div>
                            <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white flex items-center gap-3">
                                <Activity className="text-violet-500" size={36} />
                                Analytics & Risk
                            </h1>
                            <p className="text-slate-400 mt-1">Métricas algorítmicas institucionales y benchmarking.</p>
                        </div>
                    </div>

                    <div className="flex bg-slate-900 rounded-xl p-1 border border-slate-800">
                        {['1mo', '3mo', '6mo', '1y', 'ytd', 'max'].map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={cn(
                                    "px-4 py-1.5 text-sm font-semibold rounded-lg transition-all",
                                    period === p ? "bg-violet-600 text-white shadow-lg" : "text-slate-400 hover:text-white hover:bg-slate-800"
                                )}
                            >
                                {p.toUpperCase()}
                            </button>
                        ))}
                    </div>
                </header>

                {/* Dashboard Grid */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">

                    {/* Metrics Cards */}
                    <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col justify-between hover:border-slate-700 transition-colors">
                        <div className="flex justify-between items-start">
                            <p className="text-slate-400 font-medium">Volatilidad Anual</p>
                            <Info size={16} className="text-slate-600" />
                        </div>
                        <p className="text-3xl font-bold text-white mt-4">{safeMetrics.annualized_volatility_pct}%</p>
                    </div>

                    <div className={cn("bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col justify-between hover:border-slate-700 transition-colors relative overflow-hidden", isBetaHigh ? "ring-1 ring-red-500/50" : "")}>
                        {isBetaHigh && <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/10 rounded-bl-full z-0" />}
                        <div className="flex justify-between items-start z-10">
                            <p className="text-slate-400 font-medium">Beta (Mercado)</p>
                            {isBetaHigh ? <AlertTriangle size={16} className="text-red-500" /> : <Info size={16} className="text-slate-600" />}
                        </div>
                        <p className={cn("text-3xl font-bold mt-4 z-10", isBetaHigh ? "text-red-400" : "text-white")}>{safeMetrics.beta !== null ? safeMetrics.beta : 'N/A'}</p>
                    </div>

                    <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col justify-between hover:border-slate-700 transition-colors">
                        <div className="flex justify-between items-start">
                            <p className="text-slate-400 font-medium">Sharpe Ratio</p>
                            <Info size={16} className="text-slate-600" />
                        </div>
                        <p className="text-3xl font-bold text-white mt-4">{safeMetrics.sharpe_ratio} <span className="text-sm font-normal text-slate-400">vs 4% RFR</span></p>
                    </div>

                    <div className={cn("bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col justify-between hover:border-slate-700 transition-colors", isDrawdownCritical ? "ring-1 ring-orange-500/50" : "")}>
                        <div className="flex justify-between items-start">
                            <p className="text-slate-400 font-medium">Max Drawdown</p>
                            {isDrawdownCritical ? <ShieldAlert size={16} className="text-orange-500" /> : <Info size={16} className="text-slate-600" />}
                        </div>
                        <p className={cn("text-3xl font-bold mt-4", isDrawdownCritical ? "text-orange-400" : "text-white")}>{safeMetrics.max_drawdown_pct}%</p>
                    </div>

                    {/* Chart Container */}
                    <div className="col-span-1 md:col-span-4 bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col h-[450px]">
                        <div className="mb-4 flex items-center justify-between shrink-0">
                            <h3 className="text-lg font-semibold text-slate-200">Rentabilidad Histórica Acumulada (%)</h3>
                        </div>
                        {chartDataMemo && chartDataMemo.length > 0 ? (
                            <div className="flex-1 w-full min-h-0">
                                <ResponsiveContainer width="100%" height="100%" minHeight={1}>
                                    <AreaChart data={chartDataMemo} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="colorPortfolio" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                                    <XAxis dataKey="formattedDate" stroke="#64748b" fontSize={12} tickLine={false} minTickGap={30} />
                                    <YAxis stroke="#64748b" fontSize={12} tickLine={false} domain={['auto', 'auto']} tickFormatter={(value) => `${value}%`} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#f1f5f9' }}
                                        itemStyle={{ fontWeight: 600 }}
                                        formatter={(value: any) => [`${value}%`]}
                                    />
                                    <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '14px' }} iconType="circle" />
                                    <Area 
                                        type="monotone" 
                                        name="Portfolio Acumulado (%)" 
                                        dataKey="pct_portafolio" 
                                        stroke="#10b981" 
                                        strokeWidth={3} 
                                        fillOpacity={1} 
                                        fill="url(#colorPortfolio)" 
                                        dot={(props: any) => {
                                            if (props.payload.hubo_transaccion) {
                                                return <circle key={props.index} cx={props.cx} cy={props.cy} r={4} fill="#ffffff" stroke="#10b981" strokeWidth={2} />;
                                            }
                                            return null;
                                        }}
                                        activeDot={{ r: 6, fill: "#10b981", stroke: "#0f172a", strokeWidth: 2 }}
                                    />
                                    <Area type="monotone" name="S&P 500 (^GSPC) (%)" dataKey="pct_sp500" stroke="#6366f1" strokeWidth={2} fill="transparent" strokeDasharray="5 5" dot={false} />
                                </AreaChart>
                            </ResponsiveContainer>
                            </div>
                        ) : (
                           <div className="h-full flex items-center justify-center text-slate-400">
                               <TrendingUp className="mr-2" /> Sin datos para comparar en este periodo.
                           </div>
                        )}
                    </div>

                    {/* Performance Breakdown — Pilar 3 */}
                    <PerformanceBreakdown data={perfBreakdown} loading={loading} />

                    {/* Diversification Pie Charts */}
                    <div className="col-span-1 md:col-span-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Sectors */}
                        <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col h-[350px]">
                            <h3 className="text-lg font-semibold text-slate-200 mb-4">Exposición por Sector</h3>
                            <div className="flex-1 w-full min-h-0">
                                {diversification && diversification.sectors && diversification.sectors.length > 0 ? (
                                    <ResponsiveContainer width="100%" height="100%" minHeight={1}>
                                        <PieChart>
                                            <Pie 
                                                data={diversification.sectors} 
                                                dataKey="value" 
                                                nameKey="name" 
                                                cx="50%" 
                                                cy="50%" 
                                                innerRadius={60}
                                                outerRadius={90}
                                                paddingAngle={2}
                                            >
                                                {diversification.sectors.map((_entry: any, index: number) => {
                                                    const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];
                                                    return <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />;
                                                })}
                                            </Pie>
                                            <Tooltip 
                                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#f1f5f9' }}
                                                formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Valor']}
                                            />
                                            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px' }} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-slate-400">Cargando sectores...</div>
                                )}
                            </div>
                        </div>

                        {/* Countries */}
                        <div className="bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 flex flex-col h-[350px]">
                            <h3 className="text-lg font-semibold text-slate-200 mb-4">Exposición Geográfica</h3>
                            <div className="flex-1 w-full min-h-0">
                                {diversification && diversification.countries && diversification.countries.length > 0 ? (
                                    <ResponsiveContainer width="100%" height="100%" minHeight={1}>
                                        <PieChart>
                                            <Pie 
                                                data={diversification.countries} 
                                                dataKey="value" 
                                                nameKey="name" 
                                                cx="50%" 
                                                cy="50%" 
                                                innerRadius={60}
                                                outerRadius={90}
                                                paddingAngle={2}
                                            >
                                                {diversification.countries.map((_entry: any, index: number) => {
                                                    const COLORS = ['#6366f1', '#14b8a6', '#f97316', '#db2777', '#84cc16', '#eab308', '#0ea5e9'];
                                                    return <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />;
                                                })}
                                            </Pie>
                                            <Tooltip 
                                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '12px', color: '#f1f5f9' }}
                                                formatter={(value: any) => [`$${Number(value).toLocaleString()}`, 'Valor']}
                                            />
                                            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px' }} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="h-full flex items-center justify-center text-slate-400">Cargando países...</div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Valuation Table */}
                    <div className="col-span-1 md:col-span-4 bg-slate-900/50 border border-slate-800/50 rounded-3xl py-6 overflow-hidden">
                        <div className="px-6 mb-4 flex items-center justify-between">
                            <h3 className="text-lg font-semibold text-slate-200">Systemic Risk & Intrinsic Valuation</h3>
                            <span className="text-sm bg-slate-800 text-slate-400 px-3 py-1 rounded-full">Concentration Threshold: 30%</span>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-left text-sm text-slate-400">
                                <thead className="text-xs text-slate-500 uppercase bg-slate-900">
                                    <tr>
                                        <th scope="col" className="px-6 py-3">Ticker</th>
                                        <th scope="col" className="px-6 py-3">Weight (%)</th>
                                        <th scope="col" className="px-6 py-3">Raw Score</th>
                                        <th scope="col" className="px-6 py-3 text-center">Concentration Penalty</th>
                                        <th scope="col" className="px-6 py-3">Adjusted Score</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {valuation && valuation.analysis.length > 0 ? (
                                        valuation.analysis.sort((a,b) => b.weight_percentage - a.weight_percentage).map((item: ValuationAnalysis) => (
                                            <tr key={item.ticker} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                                                <td className="px-6 py-4 font-bold text-slate-200">{item.ticker}</td>
                                                <td className="px-6 py-4">
                                                    <div className="flex items-center gap-2">
                                                        <div className="w-16 h-1.5 bg-slate-800 rounded-full">
                                                            <div className={cn("h-full rounded-full", item.weight_percentage > 30 ? "bg-amber-500" : "bg-blue-500")} style={{ width: `${Math.min(item.weight_percentage, 100)}%` }} />
                                                        </div>
                                                        {item.weight_percentage}%
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">{item.original_score}/100</td>
                                                <td className="px-6 py-4 text-center">
                                                    {item.risk_penalty_multiplier < 1.0 ? (
                                                        <span className="text-red-400 bg-red-500/10 px-2 py-1 rounded-md font-medium">
                                                            -{Math.round((1 - item.risk_penalty_multiplier) * 100)}%
                                                        </span>
                                                    ) : (
                                                        <span className="text-emerald-500">-</span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4">
                                                    <span className={cn(
                                                        "px-3 py-1.5 rounded-lg font-bold text-white",
                                                        item.adjusted_score >= 80 ? "bg-emerald-500/20 text-emerald-400" :
                                                        item.adjusted_score >= 50 ? "bg-blue-500/20 text-blue-400" :
                                                        "bg-red-500/20 text-red-400"
                                                    )}>
                                                        {item.adjusted_score}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan={5} className="px-6 py-8 text-center text-slate-400">No hay activos evaluados.</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
}
