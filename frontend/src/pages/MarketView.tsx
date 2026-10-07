import { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
    ArrowLeft,
    Wallet,
    Plus,
    Search,
    Globe,
    Sparkles,
    X,
    ArrowUpRight,
    Compass,
    Briefcase,
    Filter,
} from 'lucide-react';
import { getApiUrl } from '../services/api';

import { usePortfolio } from '../hooks/usePortfolio';
import { useStockScreener } from '../hooks/useStockScreener';
import { AssetCard } from '../components/market/AssetCard';
import { TradeModal } from '../components/market/TradeModal';
import { CashModal } from '../components/market/CashModal';
import AssetDetailView from '../components/market/AssetDetailView';
import { JsonImportModal } from '../components/market/JsonImportModal';
import { ScreenerFilterBar } from '../components/screener/ScreenerFilterBar';
import { ScreenerCard } from '../components/screener/ScreenerCard';
import { ScreenerTableView } from '../components/screener/ScreenerTableView';

import type { Posicion, SearchAssetResult } from '../types';

export default function MarketView() {
    const { data, cash, loading: portfolioLoading, error: portfolioError, executeTrade, manageCash, refresh: refreshPortfolio } = usePortfolio();

    // Hook del Screener & Radar de Mercado
    const screener = useStockScreener();

    // Pestaña Principal: 'screener' (Radar & Filtros) o 'portfolio' (Portafolio Clásico)
    const [activeMainTab, setActiveMainTab] = useState<'screener' | 'portfolio'>('screener');

    // Estados Modales
    const [isTradeOpen, setTradeOpen] = useState(false);
    const [isCashOpen, setCashOpen] = useState(false);
    const [isBrokerImportOpen, setBrokerImportOpen] = useState(false);

    // Estado para Ver Detalle
    const [viewAssetTicker, setViewAssetTicker] = useState<string | null>(null);

    // Estado Selección Activo para Trading
    const [selectedAsset, setSelectedAsset] = useState<{ ticker: string; price: number } | undefined>(undefined);
    const [selectedSide, setSelectedSide] = useState<'buy' | 'sell'>('buy');

    // Estado Búsqueda Global y Autocompletado (para modo Portafolio)
    const [search, setSearch] = useState('');
    const [searchResults, setSearchResults] = useState<SearchAssetResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const searchContainerRef = useRef<HTMLDivElement>(null);

    // Debounce para búsqueda en vivo en el mercado global
    useEffect(() => {
        const query = search.trim();
        if (query.length < 1) {
            setSearchResults([]);
            setShowDropdown(false);
            return;
        }

        const timer = setTimeout(async () => {
            setIsSearching(true);
            try {
                const res = await fetch(getApiUrl(`/market/search?q=${encodeURIComponent(query)}`));
                if (res.ok) {
                    const json = await res.json();
                    setSearchResults(json.results || []);
                    setShowDropdown(true);
                }
            } catch (err) {
                console.error('Error buscando activos globales:', err);
            } finally {
                setIsSearching(false);
            }
        }, 250);

        return () => clearTimeout(timer);
    }, [search]);

    // Cerrar dropdown al hacer clic fuera
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleOpenTrade = (ticker = '', price = 0, side: 'buy' | 'sell' = 'buy') => {
        setSelectedAsset({ ticker, price });
        setSelectedSide(side);
        setTradeOpen(true);
    };

    const handleViewAsset = (ticker: string) => {
        setViewAssetTicker(ticker.trim().toUpperCase());
        setShowDropdown(false);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && search.trim()) {
            handleViewAsset(search.trim());
        }
    };

    const resumen = data?.resumen || { valor_total_portafolio: 0, ganancia_total_usd: 0, rendimiento_total_porc: 0 };
    const posiciones = data?.posiciones || [];

    const filteredPosiciones = posiciones.filter((p: Posicion) =>
        p.Ticker.toLowerCase().includes(search.toLowerCase())
    );

    const getAvgPrice = (ticker: string) => {
        const asset = posiciones.find((p) => p.Ticker === ticker);
        return asset?.Precio_Promedio;
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 font-sans">
            {/* --- HEADER --- */}
            <header className="max-w-7xl mx-auto mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div className="flex items-center gap-4">
                    <Link to="/" className="p-3 bg-slate-800/50 hover:bg-slate-700 rounded-xl transition">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold text-white tracking-tight">Mercado & Acciones</h1>
                        <div className="flex items-center gap-2 text-slate-400 text-sm">
                            <span>Valor Portafolio:</span>
                            <span className="text-emerald-400 font-bold">${resumen.valor_total_portafolio.toLocaleString()}</span>
                            <span>•</span>
                            <span>{posiciones.length} posiciones activas</span>
                        </div>
                    </div>
                </div>

                {/* --- CAJA BROKER --- */}
                <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-2 pr-4 rounded-2xl shadow-lg">
                    <button
                        onClick={() => setCashOpen(true)}
                        className="bg-indigo-600 hover:bg-indigo-500 p-3 rounded-xl transition shadow-lg shadow-indigo-500/20"
                        title="Gestionar Efectivo"
                    >
                        <Wallet size={20} className="text-white" />
                    </button>
                    <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Buying Power</p>
                        <p className="text-xl font-bold text-white">${cash.toLocaleString()}</p>
                    </div>

                    <button
                        onClick={() => setBrokerImportOpen(true)}
                        className="flex items-center gap-2 px-3 py-2 bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 text-indigo-400 hover:text-indigo-300 rounded-lg text-sm font-bold transition ml-2"
                        title="Subir archivos JSON del Broker"
                    >
                        📥 Sincronizar Broker
                    </button>

                    <button
                        onClick={() => handleOpenTrade()}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-bold transition"
                    >
                        <Plus size={16} /> Operar
                    </button>
                </div>
            </header>

            {/* --- SELECTOR DE MODO: SCREENER vs PORTAFOLIO CLÁSICO --- */}
            <div className="max-w-7xl mx-auto mb-6 flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2 bg-slate-900/80 p-1 rounded-2xl border border-slate-800">
                    <button
                        onClick={() => setActiveMainTab('screener')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                            activeMainTab === 'screener'
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                        }`}
                    >
                        <Compass size={17} />
                        <span>Radar & Filtro de Acciones</span>
                        <span className="ml-1 px-2 py-0.5 rounded-full text-[10px] bg-slate-950/60 text-indigo-300">
                            {screener.items.length}
                        </span>
                    </button>

                    <button
                        onClick={() => setActiveMainTab('portfolio')}
                        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition-all ${
                            activeMainTab === 'portfolio'
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                        }`}
                    >
                        <Briefcase size={17} />
                        <span>Mi Portafolio Clásico</span>
                        <span className="ml-1 px-2 py-0.5 rounded-full text-[10px] bg-slate-950/60 text-slate-300">
                            {posiciones.length}
                        </span>
                    </button>
                </div>

                {activeMainTab === 'screener' && screener.activeFiltersCount > 0 && (
                    <div className="hidden sm:flex items-center gap-2 text-xs text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-3 py-1.5 rounded-xl font-medium">
                        <Filter size={13} />
                        <span>{screener.activeFiltersCount} filtros activos</span>
                    </div>
                )}
            </div>

            {/* ======================================================== */}
            {/* --- SECCIÓN 1: RADAR & FILTRO DE ACCIONES (SCREENER) --- */}
            {/* ======================================================== */}
            {activeMainTab === 'screener' && (
                <div className="max-w-7xl mx-auto space-y-6">
                    {/* Barra de Filtros, Presets y Controles */}
                    <ScreenerFilterBar
                        filters={screener.filters}
                        presets={screener.presets}
                        activePresetId={screener.activePresetId}
                        availableSectors={screener.availableSectors}
                        activeFiltersCount={screener.activeFiltersCount}
                        viewMode={screener.viewMode}
                        refreshing={screener.refreshing}
                        totalCount={screener.totalItemsCount}
                        filteredCount={screener.filteredCount}
                        onUpdateFilter={screener.updateFilter}
                        onApplyPreset={screener.applyPreset}
                        onClearFilters={screener.clearFilters}
                        onRefresh={screener.refresh}
                        onSetViewMode={screener.setViewMode}
                    />

                    {/* Estado de Carga */}
                    {screener.loading ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {[...Array(8)].map((_, i) => (
                                <div key={i} className="h-64 bg-slate-900/50 border border-slate-800/60 rounded-2xl animate-pulse" />
                            ))}
                        </div>
                    ) : screener.error ? (
                        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-6 text-center text-rose-400 text-sm">
                            <p className="font-bold mb-1">Error al consultar el mercado:</p>
                            <p>{screener.error}</p>
                            <button
                                onClick={screener.refresh}
                                className="mt-4 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold transition"
                            >
                                Reintentar
                            </button>
                        </div>
                    ) : screener.items.length === 0 ? (
                        /* Estado Vacío de Filtros */
                        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-12 text-center space-y-4">
                            <div className="w-14 h-14 rounded-full bg-slate-800 flex items-center justify-center mx-auto text-slate-400">
                                <Search size={26} />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-white">No hay acciones que coincidan con estos criterios</h3>
                                <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
                                    Prueba relajando los filtros de margen de seguridad, cambiando el estado de RSI o limpiando los filtros para ver más oportunidades.
                                </p>
                            </div>
                            <button
                                onClick={screener.clearFilters}
                                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl transition"
                            >
                                Limpiar Filtros
                            </button>
                        </div>
                    ) : screener.viewMode === 'grid' ? (
                        /* Vista Cuadrícula (Cards) */
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {screener.items.map((item) => (
                                <ScreenerCard
                                    key={item.ticker}
                                    item={item}
                                    onViewDetail={handleViewAsset}
                                    onOpenTrade={(ticker, price) => handleOpenTrade(ticker, price, 'buy')}
                                    onToggleWatchlist={screener.toggleWatchlist}
                                />
                            ))}
                        </div>
                    ) : (
                        /* Vista Tabla Densa (Terminal) */
                        <ScreenerTableView
                            items={screener.items}
                            sortField={screener.sortField}
                            sortDirection={screener.sortDirection}
                            onSort={screener.handleSort}
                            onViewDetail={handleViewAsset}
                            onOpenTrade={(ticker, price) => handleOpenTrade(ticker, price, 'buy')}
                            onToggleWatchlist={screener.toggleWatchlist}
                        />
                    )}
                </div>
            )}

            {/* ======================================================== */}
            {/* --- SECCIÓN 2: PORTAFOLIO CLÁSICO & BUSCADOR GLOBAL ---- */}
            {/* ======================================================== */}
            {activeMainTab === 'portfolio' && (
                <div className="max-w-7xl mx-auto space-y-6">
                    {/* Búsqueda Global y Autocompletado */}
                    <div className="relative z-30" ref={searchContainerRef}>
                        <div className="relative">
                            <Search className="absolute left-4 top-3.5 text-slate-500" size={18} />
                            <input
                                type="text"
                                placeholder="Buscar en tu portafolio o cualquier acción global (ej: TSLA, AAPL, Palantir)..."
                                className="w-full bg-slate-900/70 border border-slate-800 rounded-xl py-3 pl-12 pr-10 text-slate-200 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/30 outline-none transition"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                onKeyDown={handleKeyDown}
                                onFocus={() => {
                                    if (searchResults.length > 0) setShowDropdown(true);
                                }}
                            />
                            {search && (
                                <button
                                    onClick={() => {
                                        setSearch('');
                                        setShowDropdown(false);
                                    }}
                                    className="absolute right-3.5 top-3.5 text-slate-500 hover:text-slate-300 transition"
                                >
                                    <X size={16} />
                                </button>
                            )}
                        </div>

                        {/* Dropdown de resultados de Yahoo Finance */}
                        {showDropdown && search.trim().length > 0 && (
                            <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden z-40 divide-y divide-slate-800/60 max-h-80 overflow-y-auto">
                                <div className="px-4 py-2 bg-slate-950/80 flex items-center justify-between text-[11px] text-slate-400 font-semibold uppercase tracking-wider">
                                    <span className="flex items-center gap-1.5">
                                        <Globe size={13} className="text-indigo-400" />
                                        Mercado Global (Explorador & Valoración)
                                    </span>
                                    <span className="text-slate-500 normal-case font-normal text-[10px]">
                                        Pulsa Enter o haz clic para analizar
                                    </span>
                                </div>

                                {isSearching ? (
                                    <div className="p-4 text-center text-xs text-slate-400">Buscando activos globales...</div>
                                ) : searchResults.length > 0 ? (
                                    searchResults.map((res) => (
                                        <div
                                            key={res.symbol}
                                            onClick={() => handleViewAsset(res.symbol)}
                                            className="p-3 hover:bg-slate-800/80 cursor-pointer flex items-center justify-between transition group"
                                        >
                                            <div className="flex items-center gap-3">
                                                <span className="font-mono font-bold text-sm text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 group-hover:bg-indigo-500/20">
                                                    {res.symbol}
                                                </span>
                                                <div>
                                                    <p className="text-sm font-semibold text-white group-hover:text-indigo-300 transition-colors">
                                                        {res.name}
                                                    </p>
                                                    <p className="text-[11px] text-slate-400">
                                                        {res.exchange} • {res.type} {res.sector ? `• ${res.sector}` : ''}
                                                    </p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-1 text-xs text-indigo-400 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                                                <span>Ver Análisis</span>
                                                <ArrowUpRight size={14} />
                                            </div>
                                        </div>
                                    ))
                                ) : (
                                    <div
                                        onClick={() => handleViewAsset(search.trim())}
                                        className="p-4 hover:bg-slate-800/80 cursor-pointer flex items-center justify-between text-xs text-indigo-300"
                                    >
                                        <span>Analizar ticker <strong>"{search.toUpperCase()}"</strong> en Yahoo Finance</span>
                                        <ArrowUpRight size={14} />
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Banner de Error Resiliente */}
                    {portfolioError && (
                        <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-6 text-center text-rose-400 text-sm">
                            <p className="font-bold mb-1">No se pudo cargar el portafolio:</p>
                            <p className="text-xs text-rose-300/80 mb-3">{portfolioError}</p>
                            <button
                                onClick={() => refreshPortfolio()}
                                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl text-xs font-bold transition shadow-lg shadow-rose-600/20"
                            >
                                Reintentar Conexión
                            </button>
                        </div>
                    )}

                    {/* Skeletons de Carga o Grid de Activos */}
                    {portfolioLoading && !data ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {[...Array(8)].map((_, i) => (
                                <div key={i} className="h-44 bg-slate-900/50 border border-slate-800/60 rounded-2xl animate-pulse" />
                            ))}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                            {/* Tarjeta de Exploración si no está en portafolio */}
                            {filteredPosiciones.length === 0 && search.trim().length > 0 && (
                                <div className="col-span-full bg-slate-900/60 border border-indigo-500/30 rounded-2xl p-8 text-center space-y-4 shadow-xl">
                                    <div className="w-12 h-12 rounded-full bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mx-auto text-indigo-400">
                                        <Sparkles size={24} />
                                    </div>
                                    <div>
                                        <h4 className="text-lg font-bold text-white">
                                            ¿Deseas analizar {search.trim().toUpperCase()} en el mercado?
                                        </h4>
                                        <p className="text-sm text-slate-400 max-w-md mx-auto mt-1">
                                            No tienes esta acción en tu portafolio, pero puedes consultar sus 7 modelos de valor intrínseco, análisis técnico y cotización en tiempo real.
                                        </p>
                                    </div>
                                    <button
                                        onClick={() => handleViewAsset(search.trim())}
                                        className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold rounded-xl shadow-lg shadow-indigo-500/20 transition-all hover:scale-105"
                                    >
                                        <Globe size={16} />
                                        Ver Análisis Completo de {search.trim().toUpperCase()}
                                    </button>
                                </div>
                            )}

                            {/* Posiciones actuales */}
                            {filteredPosiciones.map((pos: Posicion) => (
                                <AssetCard
                                    key={pos.Ticker}
                                    asset={pos}
                                    totalPortfolioValue={resumen.valor_total_portafolio}
                                    onClick={() => handleViewAsset(pos.Ticker)}
                                />
                            ))}

                            {/* Botón Agregar Activo */}
                            <button
                                onClick={() => handleOpenTrade()}
                                className="flex flex-col items-center justify-center gap-3 border-2 border-dashed border-slate-800 hover:border-indigo-500/50 hover:bg-slate-900/30 rounded-2xl min-h-[180px] transition-all group"
                            >
                                <div className="p-4 bg-slate-900 rounded-full group-hover:scale-110 transition-transform">
                                    <Plus size={24} className="text-slate-500 group-hover:text-indigo-400" />
                                </div>
                                <span className="text-slate-500 font-medium group-hover:text-slate-300">Agregar Activo</span>
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* --- MODALES COMPARTIDOS --- */}
            <TradeModal
                isOpen={isTradeOpen}
                onClose={() => setTradeOpen(false)}
                onSubmit={executeTrade}
                initialTicker={selectedAsset?.ticker}
                currentPrice={selectedAsset?.price}
                initialSide={selectedSide}
            />

            <CashModal
                isOpen={isCashOpen}
                onClose={() => setCashOpen(false)}
                currentBalance={cash}
                onSubmit={manageCash}
            />

            {/* Asset Detail View Modal (con 4 pestañas completas) */}
            {viewAssetTicker && (
                <AssetDetailView
                    ticker={viewAssetTicker}
                    onClose={() => setViewAssetTicker(null)}
                    currentAvgPrice={getAvgPrice(viewAssetTicker)}
                    onOpenTrade={handleOpenTrade}
                />
            )}

            {/* Broker Sync Modal */}
            <JsonImportModal
                isOpen={isBrokerImportOpen}
                onClose={() => setBrokerImportOpen(false)}
            />
        </div>
    );
}