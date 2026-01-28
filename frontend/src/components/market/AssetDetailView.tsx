import React, { useState, useEffect } from 'react';
import { X, RefreshCw } from 'lucide-react';
import PriceChart from './PriceChart';
import HistoryTable, { type TradeHistoryItem } from './HistoryTable';

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

    // --- Data Fetching ---
    const fetchData = async () => {
        setLoading(true);
        try {
            // 1. Chart Data
            const chartRes = await fetch(`http://localhost:8000/api/market/history/${ticker}?range=${range}`);
            const chartJson = await chartRes.json();
            if (chartJson.data) setChartData(chartJson.data);

            // 2. History Data
            const histRes = await fetch(`http://localhost:8000/api/trading/history/${ticker}`);
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
    const handleDelete = async (id: number) => {
        try {
            const res = await fetch(`http://localhost:8000/api/trading/history/${id}`, { method: 'DELETE' });
            if (res.ok) {
                fetchData(); // Refresh all
            } else {
                alert('Failed to delete trade');
            }
        } catch (e) {
            alert('Error deleting trade');
        }
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
            const res = await fetch(`http://localhost:8000/api/trading/history/${id}`, {
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
                            <button
                                onClick={() => onOpenTrade(ticker, currentAvgPrice || 0, 'sell')}
                                className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white text-sm font-bold rounded-lg transition-colors"
                            >
                                SELL
                            </button>
                        </div>
                        <button onClick={fetchData} className="p-2 bg-gray-800 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white transition-all">
                            <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
                        </button>
                        <button onClick={onClose} className="p-2 bg-gray-800 text-gray-400 rounded-full hover:bg-red-500/20 hover:text-red-400 transition-all">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">

                    {/* Chart Section */}
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
                            <p className="text-2xl font-bold text-white mt-1">${currentAvgPrice?.toFixed(2) ?? '0.00'}</p>
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

                    {/* History Section */}
                    <div>
                        <h3 className="text-lg font-semibold text-gray-200 mb-4">Trade History</h3>
                        <HistoryTable transactions={history} onEdit={handleEdit} onDelete={handleDelete} />
                    </div>

                </div>
            </div>
        </div>
    );
};

export default AssetDetailView;
