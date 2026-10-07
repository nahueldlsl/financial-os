import React from 'react';
import {
    Star,
    ArrowUpDown,
    ArrowUp,
    ArrowDown,
    ExternalLink,
    ShoppingCart,
    Zap
} from 'lucide-react';
import type { ScreenerItem } from '../../types';
import type { SortField, SortDirection } from '../../hooks/useStockScreener';

interface ScreenerTableViewProps {
    items: ScreenerItem[];
    sortField: SortField;
    sortDirection: SortDirection;
    onSort: (field: SortField) => void;
    onViewDetail: (ticker: string) => void;
    onOpenTrade: (ticker: string, price: number) => void;
    onToggleWatchlist: (ticker: string) => void;
}

export const ScreenerTableView: React.FC<ScreenerTableViewProps> = ({
    items,
    sortField,
    sortDirection,
    onSort,
    onViewDetail,
    onOpenTrade,
    onToggleWatchlist,
}) => {
    const renderSortIcon = (field: SortField) => {
        if (sortField !== field) {
            return <ArrowUpDown size={12} className="text-slate-600 group-hover:text-slate-400" />;
        }
        return sortDirection === 'asc' ? (
            <ArrowUp size={12} className="text-indigo-400" />
        ) : (
            <ArrowDown size={12} className="text-indigo-400" />
        );
    };

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto custom-scrollbar">
                <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase text-[10px] tracking-wider font-semibold">
                        <tr>
                            <th className="py-3 px-3 w-10 text-center">⭐</th>
                            <th
                                onClick={() => onSort('ticker')}
                                className="py-3 px-3 cursor-pointer hover:text-white transition group select-none"
                            >
                                <div className="flex items-center gap-1.5">
                                    <span>Activo</span>
                                    {renderSortIcon('ticker')}
                                </div>
                            </th>
                            <th
                                onClick={() => onSort('price')}
                                className="py-3 px-3 cursor-pointer hover:text-white transition group select-none"
                            >
                                <div className="flex items-center gap-1.5">
                                    <span>Precio</span>
                                    {renderSortIcon('price')}
                                </div>
                            </th>
                            <th
                                onClick={() => onSort('margin_of_safety_pct')}
                                className="py-3 px-3 cursor-pointer hover:text-white transition group select-none"
                            >
                                <div className="flex items-center gap-1.5">
                                    <span>Margen Seg.</span>
                                    {renderSortIcon('margin_of_safety_pct')}
                                </div>
                            </th>
                            <th
                                onClick={() => onSort('rsi')}
                                className="py-3 px-3 cursor-pointer hover:text-white transition group select-none"
                            >
                                <div className="flex items-center gap-1.5">
                                    <span>RSI 14</span>
                                    {renderSortIcon('rsi')}
                                </div>
                            </th>
                            <th className="py-3 px-3">Señal Confluencia</th>
                            <th className="py-3 px-3">Sector</th>
                            <th
                                onClick={() => onSort('dividend_yield_pct')}
                                className="py-3 px-3 cursor-pointer hover:text-white transition group select-none"
                            >
                                <div className="flex items-center gap-1.5">
                                    <span>Div. %</span>
                                    {renderSortIcon('dividend_yield_pct')}
                                </div>
                            </th>
                            <th className="py-3 px-3">Portafolio</th>
                            <th className="py-3 px-3 text-right">Acciones</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                        {items.map((item) => {
                            const isUndervalued = item.margin_of_safety_pct > 10;
                            const isOvervalued = item.margin_of_safety_pct < -10;

                            const mosClass = isUndervalued
                                ? 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20'
                                : isOvervalued
                                ? 'text-rose-400 bg-rose-500/10 border border-rose-500/20'
                                : 'text-amber-400 bg-amber-500/10 border border-amber-500/20';

                            const rsiClass =
                                item.rsi < 35
                                    ? 'text-emerald-400 font-bold'
                                    : item.rsi > 65
                                    ? 'text-rose-400 font-bold'
                                    : 'text-slate-300';

                            return (
                                <tr
                                    key={item.ticker}
                                    className="hover:bg-slate-800/50 transition-colors group"
                                >
                                    {/* Watchlist Star */}
                                    <td className="py-3 px-3 text-center">
                                        <button
                                            onClick={() => onToggleWatchlist(item.ticker)}
                                            className="text-slate-600 hover:text-amber-400 transition"
                                        >
                                            <Star
                                                size={14}
                                                className={item.in_watchlist ? 'text-amber-400 fill-amber-400' : ''}
                                            />
                                        </button>
                                    </td>

                                    {/* Ticker & Name */}
                                    <td className="py-3 px-3">
                                        <div className="flex items-center gap-2">
                                            <span className="font-mono font-bold text-white group-hover:text-indigo-400 transition-colors">
                                                {item.ticker}
                                            </span>
                                            {item.golden_cross && (
                                                <span title="Cruce Dorado: SMA 50 superó a SMA 200">
                                                    <Zap size={11} className="text-amber-400" />
                                                </span>
                                            )}
                                            {item.is_etf && (
                                                <span className="text-[9px] px-1 py-0.2 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                                    ETF
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-[11px] text-slate-400 truncate max-w-[140px]" title={item.company_name}>
                                            {item.company_name}
                                        </div>
                                    </td>

                                    {/* Precio Actual */}
                                    <td className="py-3 px-3 font-mono font-bold text-white">
                                        ${item.price.toFixed(2)}
                                    </td>

                                    {/* Margen de Seguridad */}
                                    <td className="py-3 px-3">
                                        {!item.is_etf ? (
                                            <span className={`inline-block font-mono font-semibold px-2 py-0.5 rounded text-[11px] ${mosClass}`}>
                                                {item.margin_of_safety_pct > 0 ? '+' : ''}
                                                {item.margin_of_safety_pct.toFixed(1)}%
                                            </span>
                                        ) : (
                                            <span className="text-[11px] text-slate-500">Índice</span>
                                        )}
                                    </td>

                                    {/* RSI 14 */}
                                    <td className="py-3 px-3">
                                        <div className="flex items-center gap-1.5">
                                            <span className={`font-mono ${rsiClass}`}>
                                                {item.rsi.toFixed(1)}
                                            </span>
                                            <span className="text-[10px] text-slate-500">
                                                ({item.rsi_label})
                                            </span>
                                        </div>
                                    </td>

                                    {/* Señal Confluencia */}
                                    <td className="py-3 px-3">
                                        <span className="text-[11px] font-medium text-slate-300">
                                            {item.confluence_label}
                                        </span>
                                    </td>

                                    {/* Sector */}
                                    <td className="py-3 px-3 text-slate-400 truncate max-w-[120px]">
                                        {item.sector}
                                    </td>

                                    {/* Dividendo % */}
                                    <td className="py-3 px-3 font-mono text-slate-300">
                                        {item.dividend_yield_pct > 0 ? `${item.dividend_yield_pct.toFixed(2)}%` : '-'}
                                    </td>

                                    {/* Portafolio */}
                                    <td className="py-3 px-3">
                                        {item.in_portfolio ? (
                                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                                                {item.portfolio_shares} acc.
                                            </span>
                                        ) : (
                                            <span className="text-[11px] text-slate-600">-</span>
                                        )}
                                    </td>

                                    {/* Acciones */}
                                    <td className="py-3 px-3 text-right">
                                        <div className="flex items-center justify-end gap-1.5">
                                            <button
                                                onClick={() => onViewDetail(item.ticker)}
                                                className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                                                title="Ver Análisis Completo"
                                            >
                                                <ExternalLink size={13} />
                                            </button>
                                            <button
                                                onClick={() => onOpenTrade(item.ticker, item.price)}
                                                className="p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition shadow-sm"
                                                title="Operar en Broker"
                                            >
                                                <ShoppingCart size={13} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
