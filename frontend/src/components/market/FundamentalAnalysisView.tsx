import React, { useState, useEffect } from 'react';
import { 
    TrendingUp, TrendingDown, Scale, ShieldCheck, AlertCircle, 
    Info, ChevronDown, ChevronUp, RefreshCw, 
    DollarSign, Activity, Percent, Layers, BarChart3 
} from 'lucide-react';
import { getApiUrl } from '../../services/api';

import type { FundamentalAnalysisResponse, ValuationModelItem } from '../../types';

interface Props {
    ticker: string;
}

export const FundamentalAnalysisView: React.FC<Props> = ({ ticker }) => {
    const [data, setData] = useState<FundamentalAnalysisResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedModel, setExpandedModel] = useState<string | null>(null);
    const [activeSection, setActiveSection] = useState<'all' | 'valuation' | 'profitability' | 'health' | 'growth'>('all');

    const fetchFundamentals = async (forceRefresh = false) => {
        if (forceRefresh) {
            setRefreshing(true);
        } else {
            setLoading(true);
        }
        setError(null);

        try {
            const url = getApiUrl(`/market/fundamentals/${ticker}${forceRefresh ? '?refresh=true' : ''}`);
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Error ${res.status}: no se pudieron cargar los datos`);
            const json: FundamentalAnalysisResponse = await res.json();
            if (json.error) {
                setError(json.error);
            } else {
                setData(json);
            }
        } catch (err: any) {
            console.error('Error fetching fundamentals:', err);
            setError(err.message || 'Error de conexión');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchFundamentals();
    }, [ticker]);

    if (loading) {
        return (
            <div className="py-16 flex flex-col items-center justify-center gap-4 text-slate-400">
                <RefreshCw size={36} className="animate-spin text-indigo-500" />
                <p className="font-mono text-sm tracking-wider">Calculando modelos de valor intrínseco y analizando balances...</p>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="p-8 bg-red-950/20 border border-red-800/40 rounded-2xl text-center space-y-4">
                <AlertCircle size={40} className="mx-auto text-red-400" />
                <h4 className="text-lg font-bold text-white">No se pudo cargar el análisis fundamental</h4>
                <p className="text-sm text-slate-400 max-w-md mx-auto">{error || 'Datos no disponibles para este activo.'}</p>
                <button
                    onClick={() => fetchFundamentals(true)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-semibold transition"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    const { summary, models, metrics, profile, current_price, is_etf, company_name } = data;

    // Helpers de formateo
    const formatNumber = (num?: number | null, prefix = '$', decimals = 2) => {
        if (num === null || num === undefined || isNaN(num)) return '-';
        return `${prefix}${num.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`;
    };

    const formatPct = (num?: number | null, suffix = '%') => {
        if (num === null || num === undefined || isNaN(num)) return '-';
        return `${num >= 0 ? '+' : ''}${num.toFixed(1)}${suffix}`;
    };

    const formatLargeNumber = (num?: number | null) => {
        if (!num) return '-';
        if (num >= 1e12) return `$${(num / 1e12).toFixed(2)}T`;
        if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
        if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
        return `$${num.toLocaleString()}`;
    };

    // Estilos de veredicto
    const getVerdictStyle = (verdict: string) => {
        switch (verdict) {
            case 'deeply_undervalued':
                return {
                    bg: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400',
                    pill: 'bg-emerald-500 text-slate-950',
                    icon: TrendingUp,
                    label: '🟢 Muy Barata (Fuerte Descuento)'
                };
            case 'undervalued':
                return {
                    bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
                    pill: 'bg-emerald-500/80 text-white',
                    icon: TrendingUp,
                    label: '🟢 Barata (Infravalorada)'
                };
            case 'fair_value':
                return {
                    bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
                    pill: 'bg-amber-500/90 text-slate-950',
                    icon: Scale,
                    label: '🟡 En Precio Justo (Fair Value)'
                };
            case 'overvalued':
                return {
                    bg: 'bg-orange-500/10 border-orange-500/30 text-orange-400',
                    pill: 'bg-orange-500 text-white',
                    icon: TrendingDown,
                    label: '🟠 Cara (Sobrevalorada)'
                };
            case 'deeply_overvalued':
                return {
                    bg: 'bg-red-500/10 border-red-500/40 text-red-400',
                    pill: 'bg-red-500 text-white',
                    icon: AlertCircle,
                    label: '🔴 Muy Cara (Fuerte Sobreprecio)'
                };
            case 'etf_index':
                return {
                    bg: 'bg-blue-500/10 border-blue-500/40 text-blue-400',
                    pill: 'bg-blue-500 text-white',
                    icon: Layers,
                    label: '🔵 ETF / Fondo Indexado'
                };
            default:
                return {
                    bg: 'bg-slate-800 border-slate-700 text-slate-300',
                    pill: 'bg-slate-700 text-white',
                    icon: Info,
                    label: 'Datos Neutrales'
                };
        }
    };

    const verdictStyle = getVerdictStyle(summary?.verdict || 'no_data');
    const VerdictIcon = verdictStyle.icon;

    return (
        <div className="space-y-6">

            {/* --- CABECERA & ACCIÓN REFRESH --- */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
                <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        {company_name} <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono">{ticker}</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                        {profile?.sector} • {profile?.industry} • {profile?.country}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => fetchFundamentals(true)}
                        disabled={refreshing}
                        className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition border border-slate-700 disabled:opacity-50"
                        title="Actualizar datos con Yahoo Finance"
                    >
                        <RefreshCw size={14} className={refreshing ? 'animate-spin text-indigo-400' : ''} />
                        {refreshing ? 'Actualizando...' : 'Recalcular'}
                    </button>
                </div>
            </div>

            {/* --- BANNER PRINCIPAL DE VALORACIÓN (GAUGE) --- */}
            <div className={`p-6 rounded-2xl border ${verdictStyle.bg} transition-all relative overflow-hidden shadow-xl`}>
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                    <div className="space-y-2">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold tracking-wide uppercase shadow-sm">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full ${verdictStyle.pill}`}>
                                <VerdictIcon size={14} className="mr-1.5 shrink-0" />
                                {summary?.verdict_label || verdictStyle.label}
                            </span>
                            {!is_etf && (
                                <span className="text-xs text-slate-400 normal-case font-normal">
                                    Promedio de {summary?.models_count || 0} modelos independientes
                                </span>
                            )}
                        </div>

                        <div className="flex items-baseline gap-4 mt-2">
                            <div>
                                <span className="text-xs text-slate-400 block font-medium">Cotización Actual</span>
                                <span className="text-3xl font-extrabold text-white tracking-tight">
                                    ${current_price.toFixed(2)}
                                </span>
                            </div>

                            {!is_etf && summary && summary.average_fair_value > 0 && (
                                <>
                                    <span className="text-2xl text-slate-600 font-light">vs</span>
                                    <div>
                                        <span className="text-xs text-slate-400 block font-medium">Valor Intrínseco Promedio</span>
                                        <span className="text-3xl font-extrabold text-indigo-400 tracking-tight">
                                            ${summary.average_fair_value.toFixed(2)}
                                        </span>
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Margen de Seguridad */}
                    {!is_etf && summary && (
                        <div className="bg-slate-950/60 p-4 rounded-xl border border-white/5 min-w-[200px]">
                            <div className="flex items-center gap-2 text-xs font-bold tracking-wider uppercase text-slate-400 mb-1">
                                <Scale size={14} className="text-indigo-400" />
                                Margen de Seguridad
                            </div>
                            <div className="flex items-baseline gap-2">
                                <span className={`text-2xl font-bold font-mono ${summary.discount_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {summary.discount_pct >= 0 ? `+${summary.discount_pct}%` : `${summary.discount_pct}%`}
                                </span>
                                <span className="text-xs text-slate-400">
                                    {summary.discount_pct >= 0 ? 'de descuento' : 'de sobreprecio'}
                                </span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-1">
                                Rango modelos: ${summary.min_fair_value.toFixed(2)} - ${summary.max_fair_value.toFixed(2)}
                            </p>
                        </div>
                    )}

                    {is_etf && summary?.etf_note && (
                        <div className="bg-slate-950/60 p-4 rounded-xl border border-white/5 max-w-md">
                            <p className="text-xs text-slate-300 leading-relaxed">
                                {summary.etf_note}
                            </p>
                        </div>
                    )}
                </div>

                {/* Barra visual de espectro de valoración */}
                {!is_etf && summary && summary.average_fair_value > 0 && summary.max_fair_value > summary.min_fair_value && (
                    <div className="mt-6 pt-4 border-t border-white/5">
                        <div className="flex justify-between text-xs text-slate-400 mb-1 font-mono">
                            <span>Mínimo: ${summary.min_fair_value.toFixed(2)}</span>
                            <span className="text-indigo-300 font-bold">Valor Justo: ${summary.average_fair_value.toFixed(2)}</span>
                            <span>Máximo: ${summary.max_fair_value.toFixed(2)}</span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full relative overflow-hidden">
                            {/* Gradiente de fondo */}
                            <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/40 via-amber-500/40 to-red-500/40" />
                        </div>
                    </div>
                )}
            </div>

            {/* --- SECCIÓN DE MODELOS DE VALORACIÓN INTRÍNSECA (GRID) --- */}
            {!is_etf && models && models.length > 0 && (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <h4 className="text-base font-bold text-white flex items-center gap-2">
                            <BarChart3 size={18} className="text-indigo-400" />
                            Modelos de Valor Intrínseco Desglosados
                        </h4>
                        <span className="text-xs text-slate-400">
                            Haz clic en cada modelo para ver sus fórmulas y supuestos
                        </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                        {models.map((model: ValuationModelItem) => {
                            const isUndervalued = model.diff_pct >= 0;
                            const isExpanded = expandedModel === model.id;

                            return (
                                <div 
                                    key={model.id}
                                    className={`bg-slate-900 border ${isExpanded ? 'border-indigo-500/50 ring-1 ring-indigo-500/20' : 'border-slate-800 hover:border-slate-700'} rounded-xl p-4 transition-all duration-200 cursor-pointer`}
                                    onClick={() => setExpandedModel(isExpanded ? null : model.id)}
                                >
                                    <div className="flex justify-between items-start gap-2 mb-2">
                                        <div>
                                            <h5 className="font-semibold text-slate-200 text-sm flex items-center gap-1.5 flex-wrap">
                                                <span>{model.name}</span>
                                                {model.is_outlier && (
                                                    <span className="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.5 rounded font-bold" title={model.outlier_reason || 'Valor atípico excluido del promedio'}>
                                                        ⚠️ Outlier (Excluido)
                                                    </span>
                                                )}
                                            </h5>
                                            <span className="text-[10px] text-slate-500 font-mono">
                                                {model.is_outlier ? 'Peso: 0x (descartado del promedio)' : `Peso: ${model.weight}x`}
                                            </span>
                                        </div>
                                        <div className="text-right">
                                            <span className={`text-lg font-bold block ${model.is_outlier ? 'text-slate-400 line-through' : 'text-white'}`}>
                                                ${model.value.toFixed(2)}
                                            </span>
                                            <span className={`text-xs font-mono font-bold flex items-center justify-end gap-0.5 ${isUndervalued ? 'text-emerald-400' : 'text-red-400'}`}>
                                                {isUndervalued ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                                                {formatPct(model.diff_pct)}
                                            </span>
                                        </div>
                                    </div>

                                    {model.is_outlier && model.outlier_reason && (
                                        <div className="mb-2 p-2 rounded bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300">
                                            {model.outlier_reason}
                                        </div>
                                    )}

                                    <p className="text-xs text-slate-400 leading-relaxed mb-3">
                                        {model.description}
                                    </p>

                                    <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-[11px] text-indigo-400 font-medium">
                                        <span>{isExpanded ? 'Ocultar supuestos' : 'Ver supuestos y variables'}</span>
                                        {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                                    </div>

                                    {/* Supuestos desplegables */}
                                    {isExpanded && (
                                        <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-1.5 bg-slate-950/60 p-3 rounded-lg text-xs">
                                            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block mb-1">
                                                Variables empleadas
                                            </span>
                                            {Object.entries(model.assumptions).map(([key, val]) => (
                                                <div key={key} className="flex justify-between text-slate-300">
                                                    <span className="text-slate-400 capitalize">{key.replace(/_/g, ' ')}:</span>
                                                    <span className="font-mono text-white">{String(val)}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* --- SECCIÓN DE MÉTRICAS FUNDAMENTALES DETALLADAS --- */}
            <div className="space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-slate-800 pb-3">
                    <h4 className="text-base font-bold text-white flex items-center gap-2">
                        <Activity size={18} className="text-indigo-400" />
                        Radiografía Fundamental Completa
                    </h4>

                    {/* Filtro de categoría */}
                    <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1 text-xs">
                        {(['all', 'valuation', 'profitability', 'health', 'growth'] as const).map(sec => (
                            <button
                                key={sec}
                                onClick={() => setActiveSection(sec)}
                                className={`px-2.5 py-1 rounded-md transition ${activeSection === sec ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'}`}
                            >
                                {sec === 'all' && 'Todo'}
                                {sec === 'valuation' && 'Múltiplos'}
                                {sec === 'profitability' && 'Rentabilidad'}
                                {sec === 'health' && 'Deuda & Salud'}
                                {sec === 'growth' && 'Crecimiento'}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Grid de Métricas */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">

                    {/* 1. VALORACIÓN Y MÚLTIPLOS */}
                    {(activeSection === 'all' || activeSection === 'valuation') && (
                        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                            <div className="flex items-center gap-2 text-indigo-400 font-bold text-xs uppercase tracking-wider">
                                <DollarSign size={14} /> Múltiplos de Valoración
                            </div>
                            <div className="space-y-2 text-xs">
                                <MetricRow label="P/E Trailing (Últimos 12m)" value={metrics.valuation.trailing_pe ? `${metrics.valuation.trailing_pe}x` : '-'} />
                                <MetricRow label="Forward P/E (Proyectado)" value={metrics.valuation.forward_pe ? `${metrics.valuation.forward_pe}x` : '-'} />
                                <MetricRow label="PEG Ratio" value={metrics.valuation.peg_ratio ? `${metrics.valuation.peg_ratio}` : '-'} highlight={metrics.valuation.peg_ratio && metrics.valuation.peg_ratio < 1.0 ? 'text-emerald-400 font-bold' : undefined} />
                                <MetricRow label="Price to Book (P/B)" value={metrics.valuation.price_to_book ? `${metrics.valuation.price_to_book}x` : '-'} />
                                <MetricRow label="Price to Sales (P/S)" value={metrics.valuation.price_to_sales ? `${metrics.valuation.price_to_sales}x` : '-'} />
                                <MetricRow label="EV / EBITDA" value={metrics.valuation.ev_to_ebitda ? `${metrics.valuation.ev_to_ebitda}x` : '-'} />
                                {metrics.valuation.nav_price && (
                                    <MetricRow label="NAV (Valor Liquidativo)" value={`$${metrics.valuation.nav_price}`} />
                                )}
                            </div>
                        </div>
                    )}

                    {/* 2. RENTABILIDAD Y MÁRGENES */}
                    {(activeSection === 'all' || activeSection === 'profitability') && (
                        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                            <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider">
                                <Percent size={14} /> Rentabilidad & Márgenes
                            </div>
                            <div className="space-y-2 text-xs">
                                <MetricRow label="Margen Neto" value={metrics.profitability.profit_margin_pct ? `${metrics.profitability.profit_margin_pct}%` : '-'} highlight="text-emerald-400" />
                                <MetricRow label="Margen Operativo" value={metrics.profitability.operating_margin_pct ? `${metrics.profitability.operating_margin_pct}%` : '-'} />
                                <MetricRow label="Margen Bruto" value={metrics.profitability.gross_margin_pct ? `${metrics.profitability.gross_margin_pct}%` : '-'} />
                                <MetricRow label="ROE (Retorno sobre Patrimonio)" value={metrics.profitability.return_on_equity_pct ? `${metrics.profitability.return_on_equity_pct}%` : '-'} />
                                <MetricRow label="ROA (Retorno sobre Activos)" value={metrics.profitability.return_on_assets_pct ? `${metrics.profitability.return_on_assets_pct}%` : '-'} />
                            </div>
                        </div>
                    )}

                    {/* 3. SALUD FINANCIERA Y DEUDA */}
                    {(activeSection === 'all' || activeSection === 'health') && (
                        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                            <div className="flex items-center gap-2 text-blue-400 font-bold text-xs uppercase tracking-wider">
                                <ShieldCheck size={14} /> Salud Financiera & Balance
                            </div>
                            <div className="space-y-2 text-xs">
                                <MetricRow label="Deuda / Patrimonio (D/E)" value={metrics.health.debt_to_equity ? `${metrics.health.debt_to_equity}%` : '-'} />
                                <MetricRow label="Ratio Corriente (Current Ratio)" value={metrics.health.current_ratio ? `${metrics.health.current_ratio}` : '-'} />
                                <MetricRow label="Prueba Ácida (Quick Ratio)" value={metrics.health.quick_ratio ? `${metrics.health.quick_ratio}` : '-'} />
                                <MetricRow label="Caja Total" value={formatLargeNumber(metrics.health.total_cash)} />
                                <MetricRow label="Deuda Total" value={formatLargeNumber(metrics.health.total_debt)} />
                                <MetricRow label="Flujo de Caja Libre (FCF)" value={formatLargeNumber(metrics.health.free_cash_flow)} highlight="text-indigo-400" />
                            </div>
                        </div>
                    )}

                    {/* 4. CRECIMIENTO, DIVIDENDOS Y MERCADO */}
                    {(activeSection === 'all' || activeSection === 'growth') && (
                        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
                            <div className="flex items-center gap-2 text-amber-400 font-bold text-xs uppercase tracking-wider">
                                <TrendingUp size={14} /> Crecimiento & Dividendos
                            </div>
                            <div className="space-y-2 text-xs">
                                <MetricRow label="Crecimiento Ingresos YoY" value={metrics.growth_and_dividends.revenue_growth_yoy_pct ? `${metrics.growth_and_dividends.revenue_growth_yoy_pct}%` : '-'} />
                                <MetricRow label="Crecimiento Beneficios YoY" value={metrics.growth_and_dividends.earnings_growth_yoy_pct ? `${metrics.growth_and_dividends.earnings_growth_yoy_pct}%` : '-'} />
                                <MetricRow label="Rentabilidad Dividendo" value={`${metrics.growth_and_dividends.dividend_yield_pct}%`} highlight="text-emerald-400 font-bold" />
                                <MetricRow label="Dividendo Anual" value={formatNumber(metrics.growth_and_dividends.dividend_rate)} />
                                <MetricRow label="Payout Ratio" value={metrics.growth_and_dividends.payout_ratio_pct ? `${metrics.growth_and_dividends.payout_ratio_pct}%` : '-'} />
                                <MetricRow label="Beta (Volatilidad vs Mercado)" value={metrics.market_stats.beta ? `${metrics.market_stats.beta}` : '-'} />
                            </div>
                        </div>
                    )}
                </div>

                {/* BARRA VISUAL DE RANGO DE 52 SEMANAS */}
                {metrics.market_stats.fifty_two_week_high && metrics.market_stats.fifty_two_week_low && (
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
                        <div className="flex justify-between items-center text-xs text-slate-400 mb-2">
                            <span className="font-semibold text-slate-300">Rango de 52 Semanas</span>
                            <span className="font-mono">
                                Cotiza al <span className="text-white font-bold">{metrics.market_stats.range_position_pct}%</span> de su rango anual
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <span className="text-xs font-mono text-slate-400 min-w-[60px]">
                                ${metrics.market_stats.fifty_two_week_low.toFixed(2)}
                            </span>
                            <div className="flex-1 h-2.5 bg-slate-800 rounded-full relative overflow-hidden">
                                <div 
                                    className="h-full bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500 rounded-full"
                                    style={{ width: `${metrics.market_stats.range_position_pct || 0}%` }}
                                />
                            </div>
                            <span className="text-xs font-mono text-slate-400 min-w-[60px] text-right">
                                ${metrics.market_stats.fifty_two_week_high.toFixed(2)}
                            </span>
                        </div>
                    </div>
                )}

                {/* DESCRIPCIÓN DEL NEGOCIO */}
                {profile?.description && profile.description !== 'Sin descripción disponible.' && (
                    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4">
                        <h5 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                            Sobre {company_name}
                        </h5>
                        <p className="text-xs text-slate-400 leading-relaxed max-h-32 overflow-y-auto">
                            {profile.description}
                        </p>
                    </div>
                )}
            </div>

        </div>
    );
};

// Subcomponente de fila de métrica
const MetricRow: React.FC<{ label: string; value: string; highlight?: string }> = ({ label, value, highlight }) => (
    <div className="flex justify-between items-center py-1 border-b border-slate-800/50 last:border-none">
        <span className="text-slate-400">{label}</span>
        <span className={`font-mono ${highlight || 'text-slate-200 font-medium'}`}>{value}</span>
    </div>
);
