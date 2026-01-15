import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Wallet, Plus, Search } from 'lucide-react';

// Asegúrate que el archivo se llame usePortfolio.ts (en inglés)
import { usePortfolio } from '../hooks/usePortfolio';
import { AssetCard } from '../components/market/AssetCard';
import { TradeModal } from '../components/market/TradeModal';
import { CashModal } from '../components/market/CashModal';

// Usamos 'import type' para interfaces
import type { Posicion } from '../types';

export default function MarketView() {
    const { data, cash, loading, error, executeTrade, manageCash } = usePortfolio();

    // Estados Modales
    const [isTradeOpen, setTradeOpen] = useState(false);
    const [isCashOpen, setCashOpen] = useState(false);

    // Estado Selección Activo
    const [selectedAsset, setSelectedAsset] = useState<{ ticker: string, price: number } | undefined>(undefined);

    // Estado Búsqueda
    const [search, setSearch] = useState('');

    const handleOpenTrade = (ticker = '', price = 0) => {
        setSelectedAsset({ ticker, price });
        setTradeOpen(true);
    };

    if (error) return <div className="p-10 text-red-500 text-center">Error: {error}</div>;
    if (loading && !data) return <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-500">Cargando portafolio...</div>;

    // Datos seguros
    const resumen = data?.resumen || { valor_total_portafolio: 0, ganancia_total_usd: 0, rendimiento_total_porc: 0 };
    const posiciones = data?.posiciones || [];

    // --- CORRECCIÓN 1: Tipado explícito en el filtro ---
    const filteredPosiciones = posiciones.filter((p: Posicion) =>
        p.Ticker.toLowerCase().includes(search.toLowerCase())
    );

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8 font-sans">

            {/* --- HEADER --- */}
            <header className="max-w-7xl mx-auto mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                <div className="flex items-center gap-4">
                    <Link to="/" className="p-3 bg-slate-800/50 hover:bg-slate-700 rounded-xl transition">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold text-white tracking-tight">Portafolio</h1>
                        <div className="flex items-center gap-2 text-slate-400 text-sm">
                            <span>Valor Total:</span>
                            <span className="text-emerald-400 font-bold">${resumen.valor_total_portafolio.toLocaleString()}</span>
                        </div>
                    </div>
                </div>

                {/* --- CAJA BROKER --- */}
                <div className="flex items-center gap-4 bg-slate-900 border border-slate-800 p-2 pr-4 rounded-2xl shadow-lg">
                    <button
                        onClick={() => setCashOpen(true)}
                        className="bg-indigo-600 hover:bg-indigo-500 p-3 rounded-xl transition shadow-lg shadow-indigo-500/20"
                    >
                        <Wallet size={20} className="text-white" />
                    </button>
                    <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Buying Power</p>
                        <p className="text-xl font-bold text-white">${cash.toLocaleString()}</p>
                    </div>
                    <div className="h-8 w-px bg-slate-800 mx-2" />
                    <button
                        onClick={() => handleOpenTrade()}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-sm font-bold transition"
                    >
                        <Plus size={16} /> Operar
                    </button>
                </div>
            </header>

            {/* --- SEARCH BAR --- */}
            <div className="max-w-7xl mx-auto mb-6">
                <div className="relative">
                    <Search className="absolute left-4 top-3.5 text-slate-500" size={18} />
                    <input
                        type="text"
                        placeholder="Buscar activo..."
                        className="w-full bg-slate-900/50 border border-slate-800 rounded-xl py-3 pl-12 pr-4 text-slate-200 focus:border-indigo-500 outline-none transition"
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                </div>
            </div>

            {/* --- GRID DE TARJETAS --- */}
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">

                {/* --- CORRECCIÓN 2: Tipado explícito en el map --- */}
                {filteredPosiciones.map((pos: Posicion) => (
                    <AssetCard
                        key={pos.Ticker}
                        asset={pos}
                        totalPortfolioValue={resumen.valor_total_portafolio}
                        onClick={() => handleOpenTrade(pos.Ticker, pos.Precio_Actual)}
                    />
                ))}

                {/* Tarjeta de "Agregar Nuevo" al final */}
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

            {/* --- MODALES --- */}
            <TradeModal
                isOpen={isTradeOpen}
                onClose={() => setTradeOpen(false)}
                onSubmit={executeTrade}
                initialTicker={selectedAsset?.ticker}
                currentPrice={selectedAsset?.price}
            />

            <CashModal
                isOpen={isCashOpen}
                onClose={() => setCashOpen(false)}
                currentBalance={cash}
                onSubmit={manageCash}
            />

        </div>
    );
}