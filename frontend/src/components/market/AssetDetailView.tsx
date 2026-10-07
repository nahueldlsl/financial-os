import React, { useState, useEffect } from 'react';
import { X, RefreshCw, LineChart, Microscope, History as HistoryIcon, Activity } from 'lucide-react';
import PriceChart from './PriceChart';
import HistoryTable, { type TradeHistoryItem } from './HistoryTable';
import { FundamentalAnalysisView } from './FundamentalAnalysisView';
import { TechnicalAnalysisView } from './TechnicalAnalysisView';
import { getApiUrl } from '../../services/api';

interface AssetDetailViewProps {
    ticker: string;
    onClose: () => void;
    currentAvgPrice?: number;
    onOpenTrade: (ticker: string, price: number, side: 'buy' | 'sell') => void;
}

const AssetDetailView: React.FC<AssetDetailViewProps> = ({ ticker, onClose, currentAvgPrice, onOpenTrade }) => {
    const [chartData, setChartData] = useState<{ time: string; value: number }[]>([]);
    const [history, setHistory] = useState<TradeHistoryItem[]>([]);
    const [range, setRange] = useState('1M');
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'fundamentals' | 'technical' | 'chart' | 'history'>('fundamentals');



    // --- Data Fetching ---
    const fetchData = async () => {
        setLoading(true);
        try {
            // 1. Chart Data
            const chartRes = await fetch(getApiUrl(`/market/history/${ticker}?range=${range}`));
            const chartJson = await chartRes.json();
            if (chartJson.data) setChartData(chartJson.data);

            // 2. History Data
            const histRes = await fetch(getApiUrl(`/trading/history/${ticker}`));
            const histJson = await histRes.json();
            if (Array.isArray(histJson)) setHistory(histJson);

        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [ticker, range]);

    // --- Actions ---
    // --- Actions ---
    const handleDelete = (id: number) => {
        // Optimistic update (HistoryTable handles API call now)
        setHistory(prev => prev.filter(tx => tx.id !== id));
    };

    const handleEdit = (tx: TradeHistoryItem) => {
        // Simple Prompt implementation for MVP to prove logic
        // Ideally a Modal, but saving time for Logic Verification first.
        const newPrice = prompt("Enter new price:", tx.precio.toString());
        if (newPrice !== null && !isNaN(parseFloat(newPrice))) {
            updateTrade(tx.id, { precio: parseFloat(newPrice) });
        }
    };

    const updateTrade = async (id: number, updates: any) => {
        try {
            const res = await fetch(getApiUrl(`/trading/history/${id}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });
            if (res.ok) {
                fetchData();
            } else {
                alert('Failed to update');
            }
        } catch (e) {
            alert('Error updating');
        }
    }

    const handleDateUpdate = async (id: number, newDate: string) => {
        try {
            const res = await fetch(getApiUrl(`/portfolio/transaction/${id}`), {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ date: newDate })
            });

            if (res.ok) {
                fetchData();
            } else {
                alert('Failed to update date');
            }
        } catch (e) {
            alert('Error updating date');
        }
    };

    return (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-2xl w-full max-w-5xl h-[90vh] overflow-hidden flex flex-col shadow-2xl">

                {/* Header */}
                <div className="p-6 border-b border-gray-800 flex justify-between items-center bg-gray-900/50">
                    <div>
                        <h2 className="text-2xl font-bold text-white">{ticker}</h2>
                        <span className="text-xs text-gray-500 uppercase tracking-wider">Broker Detail View</span>
                    </div>
                    <div className="flex gap-4 items-center">
                        <div className="flex gap-2 mr-4">
                            <button
                                onClick={() => onOpenTrade(ticker, currentAvgPrice || 0, 'buy')}
                                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-lg transition-colors"
                            >
                                BUY
                            </button>
                            {currentAvgPrice && currentAvgPrice > 0 ? (
                                <button
                                    onClick={() => onOpenTrade(ticker, currentAvgPrice, 'sell')}
                                    className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-bold rounded-lg transition-colors"
                                >
                                    SELL
                                </button>
                            ) : null}
                        </div>
                        <button onClick={fetchData} className="p-2 bg-gray-800 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white transition-all">

                            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
                        </button>
                        <button onClick={onClose} className="p-2 bg-gray-800 text-gray-400 rounded-full hover:bg-red-500/20 hover:text-red-400 transition-all">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Navigation Tabs */}
                <div className="flex border-b border-gray-800 bg-gray-900/40 px-6 gap-2 pt-2 shrink-0 overflow-x-auto">
                    <button
                        onClick={() => setActiveTab('fundamentals')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
                            activeTab === 'fundamentals'
                                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg'
                                : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-t-lg'
                        }`}
                    >
                        <Microscope size={16} />
                        Análisis Fundamental & Valoración
                    </button>
                    <button
                        onClick={() => setActiveTab('technical')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
                            activeTab === 'technical'
                                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg'
                                : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-t-lg'
                        }`}
                    >
                        <Activity size={16} />
                        Técnico & Confluencia
                    </button>
                    <button
                        onClick={() => setActiveTab('chart')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
                            activeTab === 'chart'
                                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg'
                                : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-t-lg'
                        }`}
                    >
                        <LineChart size={16} />
                        Cotización & Gráfico
                    </button>
                    <button
                        onClick={() => setActiveTab('history')}
                        className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all whitespace-nowrap ${
                            activeTab === 'history'
                                ? 'border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg'
                                : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 rounded-t-lg'
                        }`}
                    >
                        <HistoryIcon size={16} />
                        Historial de Trades ({history.length})
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">

                    {/* Tab 1: Análisis Fundamental */}
                    {activeTab === 'fundamentals' && (
                        <FundamentalAnalysisView ticker={ticker} />
                    )}

                    {/* Tab 2: Análisis Técnico & Confluencia */}
                    {activeTab === 'technical' && (
                        <TechnicalAnalysisView ticker={ticker} />
                    )}

                    {/* Tab 3: Cotización y Gráfico */}
                    {activeTab === 'chart' && (

                        <div className="space-y-6">
                            <div>
                                <div className="flex justify-between items-center mb-4">
                                    <h3 className="text-lg font-semibold text-gray-200">Price Action</h3>
                                    <div className="flex bg-gray-800 rounded-lg p-1 gap-1">
                                        {['1D', '1W', '1M', '3M', '1Y'].map(r => (
                                            <button
                                                key={r}
                                                onClick={() => setRange(r)}
                                                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${range === r ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-700'
                                                    }`}
                                            >
                                                {r}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <PriceChart data={chartData} avgPrice={currentAvgPrice} />
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-700/50">
                                    <p className="text-sm text-gray-500">Current Average Price</p>
                                    <p className="text-2xl font-bold text-white mt-1">
                                        {currentAvgPrice && currentAvgPrice > 0 ? `$${currentAvgPrice.toFixed(2)}` : 'Sin posición'}
                                    </p>
                                </div>
                                <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-700/50">
                                    <p className="text-sm text-gray-500">Total Trades</p>
                                    <p className="text-2xl font-bold text-white mt-1">{history.length}</p>
                                </div>
                                <div className="bg-gray-800/40 p-4 rounded-xl border border-gray-700/50">
                                    <p className="text-sm text-gray-500">Event Replay Mode</p>
                                    <div className="flex items-center gap-2 mt-2">
                                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                                        <span className="text-sm font-medium text-green-400">Active</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Tab 3: Historial de Trades */}
                    {activeTab === 'history' && (
                        <div>
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-lg font-semibold text-gray-200">Historial de Operaciones</h3>
                            </div>
                            {history.length > 0 ? (
                                <HistoryTable
                                    transactions={history}
                                    onEdit={handleEdit}
                                    onDelete={handleDelete}
                                    onDateUpdate={handleDateUpdate}
                                    onTradeSuccess={fetchData}
                                />
                            ) : (
                                <div className="p-12 text-center bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
                                    <p className="text-slate-300 font-medium">Aún no tienes operaciones registradas con {ticker}.</p>
                                    <p className="text-xs text-slate-500 max-w-md mx-auto">
                                        Puedes consultar sus datos fundamentales y técnicos en las otras pestañas, o pulsar el botón <strong className="text-emerald-400 font-bold">BUY</strong> para incorporar este activo a tu portafolio.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}


                </div>
            </div>
        </div>
    );
};

export default AssetDetailView;

