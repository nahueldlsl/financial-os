import { useState, useEffect, useMemo, useCallback } from 'react';
import type { ScreenerItem, ScreenerFilters, ScreenerPreset } from '../types';
import {
    fetchScreenerData,
    addTickerToWatchlist,
    removeTickerFromWatchlist,
    fetchScreenerPresets,
} from '../services/api';

export type SortField =
    | 'margin_of_safety_pct'
    | 'rsi'
    | 'price'
    | 'ticker'
    | 'dividend_yield_pct'
    | 'pe_ratio'
    | 'unrealized_profit_pct';

export type SortDirection = 'asc' | 'desc';

export const INITIAL_FILTERS: ScreenerFilters = {
    search: '',
    scope: 'all',
    valuationStatus: 'all',
    minMarginOfSafety: null,
    rsiStatus: 'all',
    onlyGoldenCross: false,
    confluenceVerdict: 'all',
    sector: 'all',
    assetType: 'all',
    portfolioProfitStatus: 'all',
    minDividendYield: null,
};

export function useStockScreener() {
    const [items, setItems] = useState<ScreenerItem[]>([]);
    const [presets, setPresets] = useState<ScreenerPreset[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [refreshing, setRefreshing] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // Estados de UI y Filtros
    const [filters, setFilters] = useState<ScreenerFilters>(INITIAL_FILTERS);
    const [activePresetId, setActivePresetId] = useState<string | null>(null);
    const [sortField, setSortField] = useState<SortField>('margin_of_safety_pct');
    const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
    const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

    // Cargar datos del Screener y Presets
    const loadData = useCallback(async (isRefresh = false) => {
        try {
            if (isRefresh) setRefreshing(true);
            else setLoading(true);
            setError(null);

            const [screenerRes, presetsRes] = await Promise.all([
                fetchScreenerData('all', isRefresh),
                fetchScreenerPresets().catch(() => ({ presets: [] })),
            ]);

            setItems(screenerRes.items || []);
            if (presetsRes.presets && presetsRes.presets.length > 0) {
                setPresets(presetsRes.presets);
            }
        } catch (err: any) {
            setError(err.message || 'Error cargando datos del radar');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        loadData(false);
    }, [loadData]);

    // Lista única de sectores calculados dinámicamente
    const availableSectors = useMemo(() => {
        const set = new Set<string>();
        items.forEach((it) => {
            if (it.sector && it.sector !== 'Desconocido' && it.sector !== 'General') {
                set.add(it.sector);
            }
        });
        return Array.from(set).sort();
    }, [items]);

    // Mutación optimista de Watchlist
    const toggleWatchlist = async (ticker: string) => {
        const cleanTicker = ticker.toUpperCase();
        const currentItem = items.find((it) => it.ticker === cleanTicker);
        const nextState = !currentItem?.in_watchlist;

        // 1. Actualización optimista instantánea
        setItems((prev) =>
            prev.map((it) => (it.ticker === cleanTicker ? { ...it, in_watchlist: nextState } : it))
        );

        // 2. Sincronización en backend
        try {
            if (nextState) {
                await addTickerToWatchlist(cleanTicker);
            } else {
                await removeTickerFromWatchlist(cleanTicker);
            }
        } catch (err) {
            console.error('Error sincronizando watchlist:', err);
            // Rollback en caso de fallo
            setItems((prev) =>
                prev.map((it) => (it.ticker === cleanTicker ? { ...it, in_watchlist: !nextState } : it))
            );
        }
    };

    // Aplicar o deseleccionar un Preset
    const applyPreset = (preset: ScreenerPreset) => {
        if (activePresetId === preset.id) {
            // Deseleccionar preset -> volver a filtros limpios manteniendo búsqueda y scope
            setActivePresetId(null);
            setFilters((prev) => ({
                ...INITIAL_FILTERS,
                search: prev.search,
                scope: prev.scope,
            }));
        } else {
            setActivePresetId(preset.id);
            setFilters((prev) => ({
                ...INITIAL_FILTERS,
                search: prev.search,
                scope: prev.scope,
                ...preset.filters,
            }));
        }
    };

    // Actualizar un filtro individual
    const updateFilter = <K extends keyof ScreenerFilters>(key: K, value: ScreenerFilters[K]) => {
        setActivePresetId(null); // Al modificar manualmente, se sale del preset
        setFilters((prev) => ({ ...prev, [key]: value }));
    };

    // Limpiar todos los filtros manteniendo búsqueda y scope
    const clearFilters = () => {
        setActivePresetId(null);
        setFilters((prev) => ({
            ...INITIAL_FILTERS,
            search: prev.search,
            scope: prev.scope,
        }));
    };

    // Cambiar ordenamiento
    const handleSort = (field: SortField) => {
        if (sortField === field) {
            setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
        } else {
            setSortField(field);
            // Por defecto descendente para métricas como margen de seguridad o dividendo
            setSortDirection(field === 'rsi' || field === 'pe_ratio' ? 'asc' : 'desc');
        }
    };

    // Conteo de filtros activos para indicador visual
    const activeFiltersCount = useMemo(() => {
        let count = 0;
        if (filters.valuationStatus !== 'all') count++;
        if (filters.minMarginOfSafety !== null) count++;
        if (filters.rsiStatus !== 'all') count++;
        if (filters.onlyGoldenCross) count++;
        if (filters.confluenceVerdict !== 'all') count++;
        if (filters.sector !== 'all') count++;
        if (filters.assetType !== 'all') count++;
        if (filters.portfolioProfitStatus !== 'all') count++;
        if (filters.minDividendYield !== null && filters.minDividendYield !== undefined) count++;
        return count;
    }, [filters]);

    // Motor de filtrado puro en cliente (Alta velocidad, <5ms)
    const filteredItems = useMemo(() => {
        return items.filter((item) => {
            // 1. Búsqueda por texto (Ticker o Nombre)
            if (filters.search.trim()) {
                const q = filters.search.trim().toLowerCase();
                const matchTicker = item.ticker.toLowerCase().includes(q);
                const matchName = item.company_name.toLowerCase().includes(q);
                if (!matchTicker && !matchName) return false;
            }

            // 2. Alcance (Scope)
            if (filters.scope === 'portfolio' && !item.in_portfolio) return false;
            if (filters.scope === 'watchlist' && !item.in_watchlist) return false;
            if (filters.scope === 'market' && item.in_portfolio) return false;

            // 3. Estado de Valoración
            if (filters.valuationStatus === 'undervalued') {
                if (item.margin_of_safety_pct < 10) return false;
            } else if (filters.valuationStatus === 'fair_value') {
                if (item.margin_of_safety_pct < -10 || item.margin_of_safety_pct > 10) return false;
            } else if (filters.valuationStatus === 'overvalued') {
                if (item.margin_of_safety_pct > -10) return false;
            }

            // 4. Margen de Seguridad Mínimo
            if (filters.minMarginOfSafety !== null && item.margin_of_safety_pct < filters.minMarginOfSafety) {
                return false;
            }

            // 5. Estado de RSI
            if (filters.rsiStatus === 'oversold' && item.rsi >= 35) return false;
            if (filters.rsiStatus === 'overbought' && item.rsi <= 65) return false;
            if (filters.rsiStatus === 'neutral' && (item.rsi < 35 || item.rsi > 65)) return false;

            // 6. Cruce Dorado
            if (filters.onlyGoldenCross && !item.golden_cross) return false;

            // 7. Señal de Confluencia
            if (filters.confluenceVerdict !== 'all' && item.confluence_verdict !== filters.confluenceVerdict) {
                return false;
            }

            // 8. Sector
            if (filters.sector !== 'all' && item.sector !== filters.sector) return false;

            // 9. Tipo de Activo (Acción vs ETF)
            if (filters.assetType === 'equity' && item.is_etf) return false;
            if (filters.assetType === 'etf' && !item.is_etf) return false;

            // 10. Rendimiento en portafolio
            if (filters.portfolioProfitStatus === 'gainers') {
                if (!item.in_portfolio || (item.unrealized_profit_pct || 0) <= 0) return false;
            } else if (filters.portfolioProfitStatus === 'losers') {
                if (!item.in_portfolio || (item.unrealized_profit_pct || 0) >= 0) return false;
            }

            // 11. Rendimiento por Dividendo Mínimo
            if (filters.minDividendYield !== null && filters.minDividendYield !== undefined) {
                if (item.dividend_yield_pct < filters.minDividendYield) return false;
            }

            return true;
        });
    }, [items, filters]);

    // Ordenamiento dinámico
    const sortedItems = useMemo(() => {
        return [...filteredItems].sort((a, b) => {
            let valA: any = a[sortField];
            let valB: any = b[sortField];

            // Manejo de nulos o indefinidos
            if (valA === null || valA === undefined) valA = -Infinity;
            if (valB === null || valB === undefined) valB = -Infinity;

            if (typeof valA === 'string') {
                return sortDirection === 'asc'
                    ? valA.localeCompare(valB)
                    : valB.localeCompare(valA);
            }

            return sortDirection === 'asc' ? valA - valB : valB - valA;
        });
    }, [filteredItems, sortField, sortDirection]);

    return {
        items: sortedItems,
        totalItemsCount: items.length,
        filteredCount: sortedItems.length,
        loading,
        refreshing,
        error,
        filters,
        presets,
        activePresetId,
        sortField,
        sortDirection,
        viewMode,
        availableSectors,
        activeFiltersCount,
        updateFilter,
        applyPreset,
        clearFilters,
        handleSort,
        setViewMode,
        toggleWatchlist,
        refresh: () => loadData(true),
    };
}
