import React, { useState, useEffect } from 'react';
import { 
    Activity, TrendingUp, Gauge, 
    Crosshair, Compass, Zap, RefreshCw, AlertTriangle, CheckCircle2, ShieldAlert
} from 'lucide-react';
import { getApiUrl } from '../../services/api';
import type { ConfluenceResponse } from '../../types';


interface Props {
    ticker: string;
}

export const TechnicalAnalysisView: React.FC<Props> = ({ ticker }) => {
    const [data, setData] = useState<ConfluenceResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchData = async (forceRefresh = false) => {
        if (forceRefresh) {
            setRefreshing(true);
        } else {
            setLoading(true);
        }
        setError(null);

        try {
            const url = getApiUrl(`/market/confluence/${ticker}${forceRefresh ? '?refresh=true' : ''}`);
            const res = await fetch(url);
            if (!res.ok) throw new Error(`Error ${res.status}: no se pudo cargar el análisis técnico`);
            const json: ConfluenceResponse = await res.json();
            if (json.error) {
                setError(json.error);
            } else {
                setData(json);
            }
        } catch (err: any) {
            console.error('Error fetching confluence:', err);
            setError(err.message || 'Error de conexión');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [ticker]);

    if (loading) {
        return (
            <div className="py-16 flex flex-col items-center justify-center gap-4 text-slate-400">
                <RefreshCw size={36} className="animate-spin text-indigo-500" />
                <p className="font-mono text-sm tracking-wider">Calculando RSI, medias móviles, bandas de Bollinger y matriz de confluencia...</p>
            </div>
        );
    }

    if (error || !data) {
        return (
            <div className="p-8 bg-red-950/20 border border-red-800/40 rounded-2xl text-center space-y-4">
                <AlertTriangle size={40} className="mx-auto text-red-400" />
                <h4 className="text-lg font-bold text-white">No se pudo cargar el análisis técnico</h4>
                <p className="text-sm text-slate-400 max-w-md mx-auto">{error || 'Datos no disponibles para este activo.'}</p>
                <button
                    onClick={() => fetchData(true)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-semibold transition"
                >
                    Reintentar
                </button>
            </div>
        );
    }

    const { confluence, technical_detail: tech, current_price, company_name } = data;

    // Estilos del veredicto de confluencia
    const getConfluenceStyle = (color: string) => {
        switch (color) {
            case 'emerald':
                return {
                    bg: 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300',
                    pill: 'bg-emerald-500 text-slate-950',
                    icon: CheckCircle2
                };
            case 'amber':
                return {
                    bg: 'bg-amber-500/10 border-amber-500/40 text-amber-300',
                    pill: 'bg-amber-500 text-slate-950',
                    icon: AlertTriangle
                };
            case 'red':
                return {
                    bg: 'bg-red-500/10 border-red-500/40 text-red-300',
                    pill: 'bg-red-500 text-white',
                    icon: ShieldAlert
                };
            case 'orange':
                return {
                    bg: 'bg-orange-500/10 border-orange-500/40 text-orange-300',
                    pill: 'bg-orange-500 text-white',
                    icon: Zap
                };
            case 'blue':
                return {
                    bg: 'bg-blue-500/10 border-blue-500/40 text-blue-300',
                    pill: 'bg-blue-500 text-white',
                    icon: Compass
                };
            default:
                return {
                    bg: 'bg-slate-800/80 border-slate-700 text-slate-300',
                    pill: 'bg-slate-700 text-white',
                    icon: Crosshair
                };
        }
    };

    const confStyle = getConfluenceStyle(confluence.color);
    const ConfIcon = confStyle.icon;

    return (
        <div className="space-y-6">

            {/* --- CABECERA --- */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
                <div>
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        {company_name} <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono">{ticker}</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                        Motor de Confluencia: Valor Fundamental (¿Qué comprar?) + Timing Técnico (¿Cuándo comprar?)
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => fetchData(true)}
                        disabled={refreshing}
                        className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition border border-slate-700 disabled:opacity-50"
                        title="Actualizar indicadores técnicos"
                    >
                        <RefreshCw size={14} className={refreshing ? 'animate-spin text-indigo-400' : ''} />
                        {refreshing ? 'Actualizando...' : 'Recalcular'}
                    </button>
                </div>
            </div>

            {/* --- HERO BANNER: MATRIZ DE CONFLUENCIA & VEREDICTO INTEGRAL --- */}
            <div className={`p-6 rounded-2xl border ${confStyle.bg} transition-all relative overflow-hidden shadow-xl`}>
                <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
                    <div className="space-y-3 max-w-2xl">
                        <div className="inline-flex items-center gap-2">
                            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-extrabold uppercase tracking-wide shadow-sm ${confStyle.pill}`}>
                                <ConfIcon size={14} />
                                {confluence.title}
                            </span>
                            <span className="text-xs text-slate-400">
                                Síntesis Fundamental + Técnica
                            </span>
                        </div>

                        <p className="text-sm text-slate-200 leading-relaxed font-medium">
                            {confluence.action}
                        </p>
                    </div>

                    {/* Resumen Dual en Cards compactas */}
                    <div className="grid grid-cols-2 gap-3 w-full lg:w-auto shrink-0">
                        {/* Pilar 1: Fundamental */}
                        <div className="bg-slate-950/70 p-3.5 rounded-xl border border-white/5 min-w-[160px]">
                            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-1">
                                🔬 Valor Fundamental
                            </span>
                            <span className={`text-sm font-bold block ${confluence.fundamental_summary.is_cheap ? 'text-emerald-400' : confluence.fundamental_summary.is_expensive ? 'text-red-400' : 'text-amber-400'}`}>
                                {confluence.fundamental_summary.label}
                            </span>
                            {confluence.fundamental_summary.fair_value > 0 && (
                                <span className="text-xs text-slate-400 font-mono mt-0.5 block">
                                    Justo: ${confluence.fundamental_summary.fair_value.toFixed(2)} ({confluence.fundamental_summary.discount_pct >= 0 ? '+' : ''}{confluence.fundamental_summary.discount_pct}%)
                                </span>
                            )}
                        </div>

                        {/* Pilar 2: Técnico */}
                        <div className="bg-slate-950/70 p-3.5 rounded-xl border border-white/5 min-w-[160px]">
                            <span className="text-[10px] text-slate-400 uppercase font-bold tracking-wider block mb-1">
                                ⚡ Timing Técnico
                            </span>
                            <span className={`text-sm font-bold block ${confluence.technical_summary.is_oversold ? 'text-emerald-400' : confluence.technical_summary.is_overbought ? 'text-red-400' : 'text-slate-200'}`}>
                                {confluence.technical_summary.label}
                            </span>
                            <span className="text-xs text-slate-400 font-mono mt-0.5 block">
                                RSI(14): <span className="text-white font-bold">{confluence.technical_summary.rsi}</span>
                            </span>
                        </div>
                    </div>
                </div>

                {/* MATRIZ DE CONFLUENCIA 2x2 VISUAL */}
                <div className="mt-6 pt-5 border-t border-white/10">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider block mb-3">
                        Posición en la Matriz de Confluencia
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                        <MatrixQuadrant
                            title="🎯 Compra Ideal"
                            desc="Barata por valor + Sobrevendida en soporte"
                            active={confluence.verdict_id === 'strong_buy_confluence'}
                            color="emerald"
                        />
                        <MatrixQuadrant
                            title="⏳ Trampa de Valor"
                            desc="Barata por valor, pero cayendo sin suelo"
                            active={confluence.verdict_id === 'value_trap_alert'}
                            color="amber"
                        />
                        <MatrixQuadrant
                            title="🏄 Momentum Trade"
                            desc="Cara por valor, pero tendencia alcista fuerte"
                            active={confluence.verdict_id === 'momentum_ride'}
                            color="orange"
                        />
                        <MatrixQuadrant
                            title="🚨 Riesgo de Corrección"
                            desc="Cara por valor + Sobrecomprada técnicamente"
                            active={confluence.verdict_id === 'correction_danger'}
                            color="red"
                        />
                    </div>
                </div>
            </div>

            {/* --- SECCIÓN DETALLADA DE INDICADORES TÉCNICOS --- */}
            <div className="space-y-4">
                <h4 className="text-base font-bold text-white flex items-center gap-2">
                    <Activity size={18} className="text-indigo-400" />
                    Indicadores Técnicos de Timing y Acción del Precio
                </h4>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

                    {/* 1. RSI (14) GAUGE & STATUS */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                                <Gauge size={14} className="text-indigo-400" /> RSI (14 periodos)
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${tech.rsi.status === 'oversold' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : tech.rsi.status === 'overbought' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-slate-800 text-slate-300'}`}>
                                {tech.rsi.label}
                            </span>
                        </div>

                        <div className="flex items-baseline justify-between">
                            <span className="text-3xl font-extrabold text-white font-mono">{tech.rsi.value}</span>
                            <span className="text-xs text-slate-400">
                                {tech.rsi.value < 30 ? '🔥 Gran descuento relativo' : tech.rsi.value > 70 ? '⚠️ Precio recalentado' : 'Equilibrio comprador/vendedor'}
                            </span>
                        </div>

                        {/* Barra de espectro RSI */}
                        <div className="space-y-1">
                            <div className="h-3 w-full bg-slate-800 rounded-full relative overflow-hidden flex">
                                <div className="w-[30%] bg-emerald-500/40" title="Zona Sobrevendida (< 30)" />
                                <div className="w-[40%] bg-slate-700/40" title="Zona Neutral (30 - 70)" />
                                <div className="w-[30%] bg-red-500/40" title="Zona Sobrecomprada (> 70)" />
                            </div>
                            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                                <span>0 (Sobreventa)</span>
                                <span>30</span>
                                <span>70</span>
                                <span>100 (Sobrecompra)</span>
                            </div>
                        </div>

                        <p className="text-[11px] text-slate-400 leading-relaxed pt-1 border-t border-slate-800">
                            Un RSI menor a 35 indica que el precio ha caído con exceso y suele preceder a rebotes alcistas.
                        </p>
                    </div>

                    {/* 2. MEDIAS MÓVILES (SMA 50 / 200 & CRUCE DORADO) */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                                <TrendingUp size={14} className="text-emerald-400" /> Medias Móviles Clave
                            </span>
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${tech.moving_averages.golden_cross ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' : 'bg-slate-800 text-slate-400'}`}>
                                {tech.moving_averages.golden_cross ? '✨ Cruce Dorado' : 'Cruce de la Muerte'}
                            </span>
                        </div>

                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Media 20 días (SMA 20):</span>
                                <span className="font-mono text-white">${tech.moving_averages.sma_20.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Media 50 días (SMA 50):</span>
                                <span className="font-mono text-white">${tech.moving_averages.sma_50.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Media 200 días (SMA 200):</span>
                                <span className="font-mono text-white">${tech.moving_averages.sma_200.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between pt-1">
                                <span className="text-slate-400">Distancia a SMA 200:</span>
                                <span className={`font-mono font-bold ${tech.moving_averages.dist_sma_200_pct >= 25 ? 'text-red-400' : tech.moving_averages.dist_sma_200_pct < 0 ? 'text-emerald-400' : 'text-slate-200'}`}>
                                    {tech.moving_averages.dist_sma_200_pct >= 0 ? '+' : ''}{tech.moving_averages.dist_sma_200_pct}%
                                </span>
                            </div>
                        </div>

                        <p className="text-[11px] text-slate-400 leading-relaxed pt-1 border-t border-slate-800">
                            {tech.moving_averages.price_above_sma_200 
                                ? 'El precio cotiza por encima de la media de 200 días, confirmando estructura alcista a largo plazo.'
                                : 'El precio cotiza por debajo de la media de 200 días, indicando debilidad estructural.'}
                        </p>
                    </div>

                    {/* 3. BANDAS DE BOLLINGER & VOLATILIDAD */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                                <Crosshair size={14} className="text-blue-400" /> Bandas de Bollinger
                            </span>
                            <span className="text-xs text-slate-400 font-mono">
                                %B: {(tech.bollinger.pct_b * 100).toFixed(0)}%
                            </span>
                        </div>

                        <div className="space-y-2 text-xs">
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Banda Superior (Resistencia):</span>
                                <span className="font-mono text-white">${tech.bollinger.upper.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Banda Media (SMA 20):</span>
                                <span className="font-mono text-white">${tech.bollinger.middle.toFixed(2)}</span>
                            </div>
                            <div className="flex justify-between py-1 border-b border-slate-800">
                                <span className="text-slate-400">Banda Inferior (Soporte):</span>
                                <span className="font-mono text-white">${tech.bollinger.lower.toFixed(2)}</span>
                            </div>
                        </div>

                        {/* Barra de posición %B */}
                        <div className="space-y-1 pt-1">
                            <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                                <span>Banda Inferior</span>
                                <span>Banda Superior</span>
                            </div>
                            <div className="h-2 w-full bg-slate-800 rounded-full relative overflow-hidden">
                                <div 
                                    className="h-full bg-blue-500 rounded-full" 
                                    style={{ width: `${Math.min(Math.max(tech.bollinger.pct_b * 100, 5), 100)}%` }}
                                />
                            </div>
                        </div>

                        <p className="text-[11px] text-slate-400 leading-relaxed pt-1 border-t border-slate-800">
                            Tocar la banda inferior (%B &lt; 15%) suele indicar sobreventa estadística a corto plazo.
                        </p>
                    </div>

                </div>

                {/* 4. MACD & SOPORTES/RESISTENCIAS EN FILA */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* MACD */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                MACD (12, 26, 9) Momentum
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${tech.macd.momentum === 'bullish' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                {tech.macd.momentum === 'bullish' ? 'Impulso Alcista' : 'Impulso Bajista'}
                            </span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs pt-1 font-mono">
                            <div className="bg-slate-950/60 p-2 rounded-lg text-center">
                                <span className="text-[10px] text-slate-500 block">Línea MACD</span>
                                <span className="text-white font-bold">{tech.macd.line}</span>
                            </div>
                            <div className="bg-slate-950/60 p-2 rounded-lg text-center">
                                <span className="text-[10px] text-slate-500 block">Señal</span>
                                <span className="text-white font-bold">{tech.macd.signal}</span>
                            </div>
                            <div className="bg-slate-950/60 p-2 rounded-lg text-center">
                                <span className="text-[10px] text-slate-500 block">Histograma</span>
                                <span className={`font-bold ${tech.macd.histogram >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {tech.macd.histogram}
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* Soportes y Resistencias a 6 meses */}
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2">
                        <div className="flex justify-between items-center">
                            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                                Soportes y Resistencias (6 Meses)
                            </span>
                            <span className="text-xs text-slate-400 font-mono">
                                Actual: ${current_price.toFixed(2)}
                            </span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                            <div className="bg-slate-950/60 p-2 rounded-lg">
                                <span className="text-[10px] text-slate-400 block font-semibold">Soporte Mínimo Reciente</span>
                                <span className="text-emerald-400 font-bold font-mono text-sm">
                                    ${tech.support_resistance.support_6m.toFixed(2)}
                                </span>
                                <span className="text-[10px] text-slate-500 block mt-0.5">
                                    a {tech.support_resistance.dist_to_support_pct}% de distancia
                                </span>
                            </div>
                            <div className="bg-slate-950/60 p-2 rounded-lg">
                                <span className="text-[10px] text-slate-400 block font-semibold">Resistencia Máxima Reciente</span>
                                <span className="text-red-400 font-bold font-mono text-sm">
                                    ${tech.support_resistance.resistance_6m.toFixed(2)}
                                </span>
                                <span className="text-[10px] text-slate-500 block mt-0.5">
                                    a +{tech.support_resistance.dist_to_resistance_pct}% de distancia
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

        </div>
    );
};

// Subcomponente de cuadrante de matriz
const MatrixQuadrant: React.FC<{ title: string; desc: string; active: boolean; color: string }> = ({ title, desc, active, color }) => {
    const activeBorder = {
        emerald: 'border-emerald-500 ring-2 ring-emerald-500/30 bg-emerald-500/20 text-emerald-200',
        amber: 'border-amber-500 ring-2 ring-amber-500/30 bg-amber-500/20 text-amber-200',
        orange: 'border-orange-500 ring-2 ring-orange-500/30 bg-orange-500/20 text-orange-200',
        red: 'border-red-500 ring-2 ring-red-500/30 bg-red-500/20 text-red-200',
    }[color] || 'border-indigo-500 bg-indigo-500/20';

    return (
        <div className={`p-3 rounded-xl border transition-all ${active ? activeBorder : 'border-slate-800 bg-slate-950/40 text-slate-400 opacity-60'}`}>
            <div className="flex items-center justify-between mb-1">
                <span className="font-bold">{title}</span>
                {active && <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />}
            </div>
            <p className="text-[11px] leading-tight opacity-90">{desc}</p>
        </div>
    );
};
