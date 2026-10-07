import React, { useState } from 'react';
import {
    Search,
    SlidersHorizontal,
    RefreshCw,
    X,
    LayoutGrid,
    Table as TableIcon,
    Sparkles,
    Check,
    ChevronDown,
    ChevronUp,
    Globe,
    Briefcase,
    Star,
    Compass
} from 'lucide-react';
import type { ScreenerFilters, ScreenerScope, ScreenerPreset } from '../../types';

interface ScreenerFilterBarProps {
    filters: ScreenerFilters;
    presets: ScreenerPreset[];
    activePresetId: string | null;
    availableSectors: string[];
    activeFiltersCount: number;
    viewMode: 'grid' | 'table';
    refreshing: boolean;
    totalCount: number;
    filteredCount: number;
    onUpdateFilter: <K extends keyof ScreenerFilters>(key: K, value: ScreenerFilters[K]) => void;
    onApplyPreset: (preset: ScreenerPreset) => void;
    onClearFilters: () => void;
    onRefresh: () => void;
    onSetViewMode: (mode: 'grid' | 'table') => void;
}

export const ScreenerFilterBar: React.FC<ScreenerFilterBarProps> = ({
    filters,
    presets,
    activePresetId,
    availableSectors,
    activeFiltersCount,
    viewMode,
    refreshing,
    totalCount,
    filteredCount,
    onUpdateFilter,
    onApplyPreset,
    onClearFilters,
    onRefresh,
    onSetViewMode,
}) => {
    const [showAdvanced, setShowAdvanced] = useState(false);

    const scopes: { id: ScreenerScope; label: string; icon: React.ReactNode }[] = [
        { id: 'all', label: 'Todo el Mercado', icon: <Globe size={15} /> },
        { id: 'portfolio', label: 'Mi Portafolio', icon: <Briefcase size={15} /> },
        { id: 'watchlist', label: 'Mi Watchlist', icon: <Star size={15} /> },
        { id: 'market', label: 'Radar Oportunidades', icon: <Compass size={15} /> },
    ];

    return (
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4 mb-6 backdrop-blur-sm">
            {/* --- FILA SUPERIOR: ALCANCE (SCOPE) + ACCIONES RÁPIDAS --- */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                {/* Scope Tabs */}
                <div className="flex items-center gap-1.5 p-1 bg-slate-950/70 border border-slate-800 rounded-xl overflow-x-auto custom-scrollbar">
                    {scopes.map((s) => {
                        const isActive = filters.scope === s.id;
                        return (
                            <button
                                key={s.id}
                                onClick={() => onUpdateFilter('scope', s.id)}
                                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                                    isActive
                                        ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                                }`}
                            >
                                {s.icon}
                                <span>{s.label}</span>
                            </button>
                        );
                    })}
                </div>

                {/* Controles de vista, refresco y contador */}
                <div className="flex items-center gap-3 self-end lg:self-center">
                    <span className="text-xs text-slate-400 font-medium">
                        Mostrando <strong className="text-white font-mono">{filteredCount}</strong> de {totalCount}
                    </span>

                    {/* Selector Vista Grid / Tabla */}
                    <div className="flex items-center p-1 bg-slate-950 border border-slate-800 rounded-xl">
                        <button
                            onClick={() => onSetViewMode('grid')}
                            className={`p-1.5 rounded-lg text-xs transition ${
                                viewMode === 'grid'
                                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                                    : 'text-slate-500 hover:text-slate-300'
                            }`}
                            title="Vista Cuadrícula"
                        >
                            <LayoutGrid size={16} />
                        </button>
                        <button
                            onClick={() => onSetViewMode('table')}
                            className={`p-1.5 rounded-lg text-xs transition ${
                                viewMode === 'table'
                                    ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                                    : 'text-slate-500 hover:text-slate-300'
                            }`}
                            title="Vista Tabla"
                        >
                            <TableIcon size={16} />
                        </button>
                    </div>

                    {/* Botón Refrescar */}
                    <button
                        onClick={onRefresh}
                        disabled={refreshing}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-300 rounded-xl text-xs font-semibold transition"
                        title="Actualizar cotizaciones y métricas"
                    >
                        <RefreshCw size={14} className={refreshing ? 'animate-spin text-indigo-400' : ''} />
                        <span className="hidden sm:inline">Actualizar</span>
                    </button>
                </div>
            </div>

            {/* --- FILA INTERMEDIA: BUSCADOR + CHIPS DE PRESETS --- */}
            <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
                {/* Search Bar */}
                <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-3 text-slate-500" size={16} />
                    <input
                        type="text"
                        placeholder="Filtrar por ticker o nombre (ej: NVDA, Apple, S&P 500)..."
                        className="w-full bg-slate-950/80 border border-slate-800 rounded-xl py-2 pl-10 pr-9 text-xs text-slate-200 placeholder-slate-500 focus:border-indigo-500 outline-none transition"
                        value={filters.search}
                        onChange={(e) => onUpdateFilter('search', e.target.value)}
                    />
                    {filters.search && (
                        <button
                            onClick={() => onUpdateFilter('search', '')}
                            className="absolute right-3 top-2.5 text-slate-500 hover:text-slate-300"
                        >
                            <X size={15} />
                        </button>
                    )}
                </div>

                {/* Botón Toggle Filtros Avanzados */}
                <button
                    onClick={() => setShowAdvanced(!showAdvanced)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold border transition ${
                        activeFiltersCount > 0 || showAdvanced
                            ? 'bg-indigo-600/10 border-indigo-500/40 text-indigo-400'
                            : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                >
                    <SlidersHorizontal size={15} />
                    <span>Filtros Avanzados</span>
                    {activeFiltersCount > 0 && (
                        <span className="w-5 h-5 rounded-full bg-indigo-500 text-white text-[10px] font-bold flex items-center justify-center">
                            {activeFiltersCount}
                        </span>
                    )}
                    {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
            </div>

            {/* --- PRESETS RÁPIDOS (1-CLICK ESTRATEGIAS) --- */}
            {presets.length > 0 && (
                <div className="pt-1">
                    <div className="flex items-center gap-2 mb-2">
                        <Sparkles size={13} className="text-amber-400" />
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                            Estrategias Rápidas Cuantitativas
                        </span>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {presets.map((preset) => {
                            const isSelected = activePresetId === preset.id;
                            return (
                                <button
                                    key={preset.id}
                                    onClick={() => onApplyPreset(preset)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border transition-all ${
                                        isSelected
                                            ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 font-bold shadow-md shadow-amber-500/10 scale-[1.02]'
                                            : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-800/40'
                                    }`}
                                    title={preset.description}
                                >
                                    <span>{preset.icon}</span>
                                    <span>{preset.label}</span>
                                    {isSelected && <Check size={13} className="text-amber-400" />}
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}

            {/* --- PANEL DESPLEGABLE DE FILTROS AVANZADOS --- */}
            {showAdvanced && (
                <div className="pt-4 border-t border-slate-800 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-in fade-in-50 duration-200">
                    {/* 1. Margen de Seguridad Mínimo */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Margen de Seguridad Mínimo</label>
                        <select
                            value={filters.minMarginOfSafety ?? 'all'}
                            onChange={(e) =>
                                onUpdateFilter(
                                    'minMarginOfSafety',
                                    e.target.value === 'all' ? null : Number(e.target.value)
                                )
                            }
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Cualquiera</option>
                            <option value="0">≥ 0% (Al menos Valor Justo)</option>
                            <option value="15">≥ 15% (Descuento Atractivo)</option>
                            <option value="25">≥ 25% (Fuerte Descuento)</option>
                            <option value="40">≥ 40% (Oportunidad Profunda)</option>
                        </select>
                    </div>

                    {/* 2. Estado de Valoración */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Estado de Valoración</label>
                        <select
                            value={filters.valuationStatus}
                            onChange={(e) => onUpdateFilter('valuationStatus', e.target.value as any)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Todos los estados</option>
                            <option value="undervalued">Infravaloradas (Baratas)</option>
                            <option value="fair_value">En Valor Justo</option>
                            <option value="overvalued">Sobrevaloradas (Caras)</option>
                        </select>
                    </div>

                    {/* 3. Indicador RSI (14) */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Timing RSI (14)</label>
                        <select
                            value={filters.rsiStatus}
                            onChange={(e) => onUpdateFilter('rsiStatus', e.target.value as any)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Cualquier RSI</option>
                            <option value="oversold">Sobrevendida (&lt; 35 - Rebote)</option>
                            <option value="neutral">Zona Neutral (35 - 65)</option>
                            <option value="overbought">Sobrecomprada (&gt; 65)</option>
                        </select>
                    </div>

                    {/* 4. Señal de Confluencia */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Matriz de Confluencia</label>
                        <select
                            value={filters.confluenceVerdict}
                            onChange={(e) => onUpdateFilter('confluenceVerdict', e.target.value as any)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Todas las señales</option>
                            <option value="strong_buy_confluence">🎯 Oportunidad Fuerte</option>
                            <option value="value_trap_alert">⚠️ Trampa de Valor</option>
                            <option value="momentum_ride">🚀 Momentum Alcista</option>
                            <option value="correction_danger">📉 Riesgo de Corrección</option>
                        </select>
                    </div>

                    {/* 5. Sector Económico */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Sector Económico</label>
                        <select
                            value={filters.sector}
                            onChange={(e) => onUpdateFilter('sector', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Todos los Sectores</option>
                            {availableSectors.map((sec) => (
                                <option key={sec} value={sec}>
                                    {sec}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* 6. Tipo de Activo */}
                    <div className="space-y-1.5">
                        <label className="text-[11px] font-bold uppercase text-slate-400">Tipo de Instrumento</label>
                        <select
                            value={filters.assetType}
                            onChange={(e) => onUpdateFilter('assetType', e.target.value as any)}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2 text-xs text-slate-200 focus:border-indigo-500 outline-none"
                        >
                            <option value="all">Acciones y ETFs</option>
                            <option value="equity">Solo Acciones Corporativas</option>
                            <option value="etf">Solo ETFs / Índices</option>
                        </select>
                    </div>

                    {/* 7. Cruce Dorado (Golden Cross) */}
                    <div className="flex items-center gap-3 pt-6">
                        <input
                            type="checkbox"
                            id="golden_cross_toggle"
                            checked={filters.onlyGoldenCross}
                            onChange={(e) => onUpdateFilter('onlyGoldenCross', e.target.checked)}
                            className="w-4 h-4 text-indigo-600 rounded bg-slate-950 border-slate-800 focus:ring-indigo-500 focus:ring-offset-slate-900"
                        />
                        <label htmlFor="golden_cross_toggle" className="text-xs text-slate-300 font-semibold cursor-pointer">
                            Solo con Cruce Dorado (SMA 50 &gt; 200)
                        </label>
                    </div>

                    {/* 8. Botón Limpiar Filtros */}
                    <div className="flex items-end justify-end pt-4">
                        <button
                            onClick={onClearFilters}
                            disabled={activeFiltersCount === 0 && !filters.search}
                            className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 disabled:opacity-30 text-slate-300 rounded-xl text-xs font-semibold transition"
                        >
                            <X size={14} />
                            <span>Limpiar Filtros</span>
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};
