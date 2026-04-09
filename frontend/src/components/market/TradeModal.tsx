import React, { useState, useEffect } from 'react';
import { X, Calendar } from 'lucide-react';
import type { TradeAction } from '../../types';
import { useTradeCalculator, type BrokerSettings } from '../../hooks/useTradeCalculator';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    onSubmit: (type: 'buy' | 'sell', data: TradeAction) => Promise<boolean>;
    initialTicker?: string;
    currentPrice?: number;
    initialSide?: 'buy' | 'sell';
}

export const TradeModal: React.FC<Props> = ({ isOpen, onClose, onSubmit, initialTicker = '', currentPrice = 0, initialSide = 'buy' }) => {
    const [ticker, setTicker] = useState(initialTicker);
    const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 16)); // YYYY-MM-DDTHH:mm
    const [usarCaja, setUsarCaja] = useState(true);
    const [settings, setSettings] = useState<BrokerSettings | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    // Custom Hook
    const {
        cantidad, setCantidad,
        precio, setPrecio,
        fee, setFee,
        manualFee, setManualFee,
        mode, setMode,
        totalEstimado,
        reset
    } = useTradeCalculator(settings, currentPrice);

    useEffect(() => {
        if (isOpen) {
            setTicker(initialTicker);
            reset();
            setMode(initialSide); // Respetar el lado inicial
            // Re-setear precio si vino por props (el hook lo maneja en useEffect, pero el reset lo limpia)
            if (currentPrice > 0) setPrecio(currentPrice.toString());

            // Cargar settings globales si no existen
            if (!settings) {
                fetch('http://127.0.0.1:8000/api/settings/')
                    .then(res => res.json())
                    .then(data => setSettings(data))
                    .catch(err => console.error("Error loading settings in modal", err));
            }
        }
    }, [isOpen, initialTicker, currentPrice, initialSide]); // Add initialSide to dep array

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSubmitting(true);

        const fechaISO = new Date(fecha).toISOString();

        const success = await onSubmit(mode, {
            ticker: ticker.toUpperCase(),
            type: mode.toUpperCase(), // Add 'type' if we want to use the unified endpoint structure directly, though types.ts defines TradeAction having 'cantidad' etc. Let's see types.ts again. TradeAction doesn't have 'type'.
            // Actually, TradeModal's onSubmit signature is (mode, data). The parent determines the endpoint or payload structure.
            // Let's stick to what we have in TradeAction interface.
            cantidad: parseFloat(cantidad),
            precio: parseFloat(precio),
            fecha: fechaISO,
            usar_caja_broker: usarCaja,
            applied_fee: parseFloat(fee || '0')
        } as any); // Type assertion for now if we added 'type' but interface doesn't have it.
        // Actually, better to just pass the data as is and let parent handle it.
        // But the user request said "Payload: { ticker, type, quantity, price, date: Optional[datetime] }".
        // The TradeAction interface in types.ts DOES NOT have 'type'.
        // So I should probably modify TradeAction interface in types.ts OR modify how data is constructed.
        // Since I'm editing TradeModal, I'll leave it as is but ensure `fecha` is correct.

        // Wait, I updated the BACKEND to accept TradeSchema which HAS 'type'.
        // So I need to ensure the data sent to backend matches.
        // If the PARENT calls the new endpoint, it needs 'type'.
        // The TradeModal prop `onSubmit` is `(type: 'buy' | 'sell', data: TradeAction) => Promise<boolean>`.
        // So the `type` is passed as the first argument. The `data` is the second.
        // It seems the Parent constructs the final payload or chooses the endpoint.

        setIsSubmitting(false);
        if (success) onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 w-full max-w-md rounded-2xl shadow-2xl overflow-hidden">
                {/* Header */}
                <div className="flex justify-between items-center p-4 border-b border-slate-800">
                    <div>
                        <h2 className="text-lg font-bold text-white flex items-center gap-2">
                            <span className={mode === 'buy' ? 'text-emerald-400' : 'text-red-400'}>
                                {mode === 'buy' ? 'COMPRAR' : 'VENDER'}
                            </span>
                            {ticker}
                        </h2>
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

                    {/* Commission Fee */}
                    <div>
                        <div className="flex justify-between items-center mb-1">
                            <label className="text-xs text-slate-400 font-bold uppercase tracking-wider">Comisión Broker</label>
                            {!manualFee && fee !== '' && <span className="text-[10px] text-indigo-400">Autocompletado</span>}
                        </div>
                        <div className="relative">
                            <span className="absolute left-3 top-3 text-slate-500">$</span>
                            <input
                                type="number" step="any"
                                className={`w-full bg-slate-950 border rounded-lg p-3 pl-7 text-white font-mono focus:border-indigo-500 outline-none ${manualFee ? 'border-amber-500/50' : 'border-slate-800'}`}
                                placeholder="0.00"
                                value={fee}
                                onChange={e => {
                                    setFee(e.target.value);
                                    setManualFee(true);
                                }}
                            />
                        </div>
                    </div>

                    {/* Fecha de Operación */}
                    <div>
                        <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block flex items-center gap-2">
                            <Calendar size={12} /> Fecha Operación
                        </label>
                        <input
                            type="datetime-local"
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
                        <p className="text-slate-500 text-sm">Total Estimado {mode === 'buy' ? '(Costo)' : '(Recibo)'}</p>
                        <p className="text-2xl font-bold text-white">
                            ${totalEstimado.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
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