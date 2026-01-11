import React, { useState } from 'react';
import { PlusCircle } from 'lucide-react';
import type { Movimiento } from '../types';

interface Props {
    onSave: (mov: Movimiento) => Promise<void>;
}

export const TransactionForm: React.FC<Props> = ({ onSave }) => {
    const [monto, setMonto] = useState('');
    const [categoria, setCategoria] = useState('');
    const [moneda, setMoneda] = useState<'USD' | 'UYU'>('UYU');
    const [tipo, setTipo] = useState<'ingreso' | 'gasto'>('gasto');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!monto || !categoria) return;

        setIsSubmitting(true);
        try {
            await onSave({
                tipo,
                monto: parseFloat(monto),
                moneda,
                categoria
            });
            // Limpiar formulario solo si tuvo éxito
            setMonto('');
            setCategoria('');
        } catch (error) {
            console.error("Error al guardar desde el form", error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="bg-slate-900 p-5 rounded-2xl border border-slate-800 shadow-md">
            <h3 className="font-semibold mb-4 flex items-center gap-2 text-slate-100">
                <PlusCircle size={18} className="text-emerald-400" /> Agregar Movimiento
            </h3>

            <form onSubmit={handleSubmit} className="space-y-3">
                {/* Selector Tipo */}
                <div className="flex bg-slate-950 rounded-lg p-1 border border-slate-800">
                    <button type="button" onClick={() => setTipo('gasto')} className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-all ${tipo === 'gasto' ? 'bg-red-500/20 text-red-400 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}>Gasto</button>
                    <button type="button" onClick={() => setTipo('ingreso')} className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-all ${tipo === 'ingreso' ? 'bg-emerald-500/20 text-emerald-400 shadow-sm' : 'text-slate-500 hover:text-slate-300'}`}>Ingreso</button>
                </div>

                {/* Input Concepto */}
                <input
                    type="text"
                    placeholder="Concepto (ej: Supermercado)"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition"
                    value={categoria}
                    onChange={e => setCategoria(e.target.value)}
                />

                {/* Input Monto y Moneda */}
                <div className="flex gap-2">
                    <div className="relative w-2/3">
                        <span className="absolute left-3 top-2.5 text-slate-500">$</span>
                        <input
                            type="number"
                            placeholder="0.00"
                            step="0.01"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 pl-7 text-sm text-white placeholder-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition"
                            value={monto}
                            onChange={e => setMonto(e.target.value)}
                        />
                    </div>
                    <select
                        className="w-1/3 bg-slate-950 border border-slate-800 rounded-lg p-2 text-sm text-white focus:border-indigo-500 outline-none cursor-pointer"
                        value={moneda}
                        onChange={(e) => setMoneda(e.target.value as 'USD' | 'UYU')}
                    >
                        <option value="UYU">UYU</option>
                        <option value="USD">USD</option>
                    </select>
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting || !monto || !categoria}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-2.5 rounded-lg transition-colors text-sm shadow-lg shadow-indigo-600/20"
                >
                    {isSubmitting ? 'Guardando...' : 'Guardar Movimiento'}
                </button>
            </form>
        </div>
    );
};