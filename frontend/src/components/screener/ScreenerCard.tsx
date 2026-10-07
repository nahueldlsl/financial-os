import React from 'react';
import {
    Star,
    Sparkles,
    TrendingUp,
    TrendingDown,
    Zap,
    ExternalLink,
    ShoppingCart,
    Layers,
    AlertTriangle,
    ShieldCheck
} from 'lucide-react';
import type { ScreenerItem } from '../../types';

interface ScreenerCardProps {
    item: ScreenerItem;
    onViewDetail: (ticker: string) => void;
    onOpenTrade: (ticker: string, price: number) => void;
    onToggleWatchlist: (ticker: string) => void;
}

export const ScreenerCard: React.FC<ScreenerCardProps> = ({
    item,
    onViewDetail,
    onOpenTrade,
    onToggleWatchlist,
}) => {
    const isUndervalued = item.margin_of_safety_pct > 10;
    const isOvervalued = item.margin_of_safety_pct < -10;

    // Colores para el margen de seguridad
    const mosColor = isUndervalued
        ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
        : isOvervalued
        ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
        : 'text-amber-400 bg-amber-500/10 border-amber-500/20';

    // Colores para el RSI
    const rsiColor =
        item.rsi < 35
            ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
            : item.rsi > 65
            ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
            : 'text-slate-400 bg-slate-800/60 border-slate-700/40';

    // Badge de confluencia
    const getConfluenceBadge = () => {
        switch (item.confluence_verdict) {
            case 'strong_buy_confluence':
                return {
                    label: 'Oportunidad Fuerte',
                    icon: <Sparkles size={12} className="text-emerald-400" />,
                    classes: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
                };
            case 'value_trap_alert':
                return {
                    label: 'Alerta Trampa Valor',
                    icon: <AlertTriangle size={12} className="text-amber-400" />,
                    classes: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
                };
            case 'momentum_ride':
                return {
                    label: 'Momentum Alcista',
                    icon: <TrendingUp size={12} className="text-blue-400" />,
                    classes: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
                };
            case 'correction_danger':
                return {
                    label: 'Riesgo Corrección',
                    icon: <TrendingDown size={12} className="text-rose-400" />,
                    classes: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
                };
            default:
                return {
                    label: 'Neutro / Seguimiento',
                    icon: <ShieldCheck size={12} className="text-slate-400" />,
                    classes: 'bg-slate-800/50 border-slate-700 text-slate-400',
                };
        }
    };

    const confluence = getConfluenceBadge();

    return (
        <div className="bg-slate-900/80 hover:bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 shadow-lg hover:shadow-xl transition-all duration-200 flex flex-col justify-between group">
            <div>
                {/* --- HEADER: TICKER + EMPRESA + WATCHLIST BUTTON --- */}
                <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono font-bold text-base text-white group-hover:text-indigo-400 transition-colors">
                                {item.ticker}
                            </span>
                            {item.is_etf ? (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                    ETF
                                </span>
                            ) : (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/50">
                                    Acción
                                </span>
                            )}
                            {item.golden_cross && (
                                <span
                                    className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center gap-1"
                                    title="Cruce Dorado: SMA 50 superó a SMA 200"
                                >
                                    <Zap size={10} /> Cruce Dorado
                                </span>
                            )}
                        </div>
                        <h4 className="text-xs text-slate-400 truncate" title={item.company_name}>
                            {item.company_name}
                        </h4>
                        <p className="text-[11px] text-slate-500 truncate mt-0.5">
                            {item.sector}
                        </p>
                    </div>

                    {/* Botón Favorito / Watchlist ⭐ */}
                    <button
                        onClick={() => onToggleWatchlist(item.ticker)}
                        className={`p-2 rounded-xl transition ${
                            item.in_watchlist
                                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                                : 'text-slate-500 hover:text-amber-400 hover:bg-slate-800'
                        }`}
                        title={item.in_watchlist ? 'Quitar de Watchlist' : 'Agregar a Watchlist'}
                    >
                        <Star size={16} className={item.in_watchlist ? 'fill-amber-400' : ''} />
                    </button>
                </div>

                {/* --- PRECIO Y VALOR INTRÍNSECO --- */}
                <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-3 mb-3">
                    <div className="flex items-baseline justify-between mb-1.5">
                        <span className="text-xl font-bold font-mono text-white">
                            ${item.price.toFixed(2)}
                        </span>
                        {!item.is_etf && item.fair_value > 0 && (
                            <span className="text-[11px] text-slate-400 font-mono">
                                V. Justo: <strong className="text-slate-200">${item.fair_value.toFixed(2)}</strong>
                            </span>
                        )}
                    </div>

                    {/* Barra de Margen de Seguridad */}
                    {!item.is_etf ? (
                        <div className="space-y-1">
                            <div className="flex items-center justify-between text-[11px]">
                                <span className="text-slate-400">Margen de Seguridad:</span>
                                <span className={`font-bold font-mono px-1.5 py-0.5 rounded border text-[11px] ${mosColor}`}>
                                    {item.margin_of_safety_pct > 0 ? '+' : ''}
                                    {item.margin_of_safety_pct.toFixed(1)}%
                                </span>
                            </div>
                            <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                    className={`h-full rounded-full transition-all duration-500 ${
                                        isUndervalued ? 'bg-emerald-500' : isOvervalued ? 'bg-rose-500' : 'bg-amber-500'
                                    }`}
                                    style={{
                                        width: `${Math.min(100, Math.max(10, Math.abs(item.margin_of_safety_pct)))}%`,
                                    }}
                                />
                            </div>
                        </div>
                    ) : (
                        <div className="flex items-center gap-1.5 text-[11px] text-blue-400">
                            <Layers size={13} />
                            <span>Canasta indexada diversificada</span>
                        </div>
                    )}
                </div>

                {/* --- MÉTRICAS SECUNDARIAS: RSI & CONFLUENCIA --- */}
                <div className="grid grid-cols-2 gap-2 mb-3">
                    {/* RSI */}
                    <div className={`p-2 rounded-xl border text-xs flex flex-col justify-between ${rsiColor}`}>
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-slate-400">RSI (14)</span>
                            <span className="font-mono font-bold">{item.rsi.toFixed(1)}</span>
                        </div>
                        <span className="text-[10px] mt-1 font-semibold truncate">
                            {item.rsi_label}
                        </span>
                    </div>

                    {/* Confluencia */}
                    <div className={`p-2 rounded-xl border text-xs flex flex-col justify-between ${confluence.classes}`}>
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-slate-400">Señal</span>
                            {confluence.icon}
                        </div>
                        <span className="text-[10px] mt-1 font-semibold truncate">
                            {confluence.label}
                        </span>
                    </div>
                </div>

                {/* --- SI ESTÁ EN PORTAFOLIO: ESTADO DE POSICIÓN --- */}
                {item.in_portfolio && (
                    <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-2.5 mb-3 text-xs flex items-center justify-between">
                        <span className="text-slate-400 text-[11px]">
                            En cartera: <strong>{item.portfolio_shares}</strong> acc.
                        </span>
                        {item.unrealized_profit_pct !== undefined && item.unrealized_profit_pct !== null && (
                            <span
                                className={`font-mono font-bold text-[11px] ${
                                    item.unrealized_profit_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'
                                }`}
                            >
                                {item.unrealized_profit_pct >= 0 ? '+' : ''}
                                {item.unrealized_profit_pct.toFixed(1)}%
                            </span>
                        )}
                    </div>
                )}
            </div>

            {/* --- FOOTER: ACCIONES RÁPIDAS --- */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                <button
                    onClick={() => onViewDetail(item.ticker)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition"
                >
                    <ExternalLink size={14} />
                    <span>Ver Análisis</span>
                </button>
                <button
                    onClick={() => onOpenTrade(item.ticker, item.price)}
                    className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl transition shadow-md shadow-indigo-600/20 flex items-center gap-1.5"
                    title="Operar en Broker"
                >
                    <ShoppingCart size={14} />
                    <span>Operar</span>
                </button>
            </div>
        </div>
    );
};
