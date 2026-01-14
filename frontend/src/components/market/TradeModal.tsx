import React, { useState, useEffect } from 'react';
import { X, Calendar } from 'lucide-react';
import type { TradeAction } from '../../types';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (type: 'buy' | 'sell', data: TradeAction) => Promise<boolean>;
    initialTicker?: string; // Si venimos de clickear una carta
    currentPrice?: number;
}

export const TradeModal: React.FC<Props> = ({ isOpen, onClose, onSubmit, initialTicker = '', currentPrice = 0 }) => {
    const [mode, setMode] = useState<'buy' | 'sell'>('buy');
    const [ticker, setTicker] = useState(initialTicker);
    const [cantidad, setCantidad] = useState('');
    const [precio, setPrecio] = useState(currentPrice.toString());
    const [fecha, setFecha] = useState(new Date().toISOString().split('T')[0]); // Hoy YYYY-MM-DD
    const [usarCaja, setUsarCaja] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setTicker(initialTicker);
            setPrecio(currentPrice > 0 ? currentPrice.toString() : '');
            setCantidad('');
            setMode('buy');
        }
    }, [isOpen, initialTicker, currentPrice]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);

        // Formatear fecha para backend (ISO con hora 00:00)
        const fechaISO = new Date(fecha).toISOString();

        const success = await onSubmit(mode, {
            ticker: ticker.toUpperCase(),
            cantidad: parseFloat(cantidad),
            precio: parseFloat(precio),
            fecha: fechaISO,
            usar_caja_broker: usarCaja
        });

        setIsSubmitting(false);
        if (success) onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-slate-800">
                    <div className="flex gap-2 bg-slate-950 p-1 rounded-lg">
                        <button
                            onClick={() => setMode('buy')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${mode === 'buy' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                        >
                            COMPRAR
                        </button>
                        <button
                            onClick={() => setMode('sell')}
                            className={`px-4 py-1.5 text-sm font-bold rounded-md transition-all ${mode === 'sell' ? 'bg-red-600 text-white shadow' : 'text-slate-400 hover:text-white'}`}
                        >
                            VENDER
                        </button>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
                </div>

                {/* Body */}
                <form onSubmit={handleSubmit} className="p-6 space-y-4">

                    {/* Ticker */}
                    <div>
                        <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block">Ticker (Símbolo)</label>
                        <input
                            type="text"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white font-mono uppercase focus:border-indigo-500 outline-none"
                            placeholder="Ej: AAPL"
                            value={ticker}
                            onChange={e => setTicker(e.target.value)}
                            required
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block">Cantidad</label>
                            <input
                                type="number" step="any"
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white font-mono focus:border-indigo-500 outline-none"
                                placeholder="0.00"
                                value={cantidad}
                                onChange={e => setCantidad(e.target.value)}
                                required
                            />
                        </div>
                        <div>
                            <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block">Precio Unit.</label>
                            <input
                                type="number" step="any"
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white font-mono focus:border-indigo-500 outline-none"
                                placeholder="0.00"
                                value={precio}
                                onChange={e => setPrecio(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    {/* Fecha de Operación (Para historial y precio promedio) */}
                    <div>
                        <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block flex items-center gap-2">
                            <Calendar size={12} /> Fecha Operación
                        </label>
                        <input
                            type="date"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-indigo-500 outline-none"
                            value={fecha}
                            onChange={e => setFecha(e.target.value)}
                        />
                    </div>

                    {/* Checkbox Caja */}
                    <div className="flex items-center gap-3 p-3 bg-slate-950/50 rounded-lg border border-slate-800/50">
                        <input
                            type="checkbox"
                            id="useCash"
                            checked={usarCaja}
                            onChange={e => setUsarCaja(e.target.checked)}
                            className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-indigo-500"
                        />
                        <label htmlFor="useCash" className="text-sm text-slate-300 cursor-pointer select-none">
                            {mode === 'buy' ? 'Descontar de Caja Broker' : 'Depositar en Caja Broker'}
                        </label>
                    </div>

                    {/* Total Estimado */}
                    <div className="text-center py-2">
                        <p className="text-slate-500 text-sm">Total Operación</p>
                        <p className="text-2xl font-bold text-white">
                            ${(parseFloat(cantidad || '0') * parseFloat(precio || '0')).toLocaleString()}
                        </p>
                    </div>

                    <button
                        type="submit"
                        disabled={isSubmitting}
                        className={`w-full py-3 rounded-lg font-bold text-white transition-all ${mode === 'buy'
                                ? 'bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-500/20'
                                : 'bg-red-600 hover:bg-red-500 shadow-lg shadow-red-500/20'
                            }`}
                    >
                        {isSubmitting ? 'Procesando...' : (mode === 'buy' ? 'CONFIRMAR COMPRA' : 'CONFIRMAR VENTA')}
                    </button>
                </form>
            </div>
        </div>
    );
};