import React from 'react';
import { PlusCircle, MinusCircle, DollarSign } from 'lucide-react';
import type { Movimiento } from '../types';

interface Props {
    movimientos: Movimiento[];
    exchangeRate: number;
}

export const TransactionList: React.FC<Props> = ({ movimientos, exchangeRate }) => {
    if (movimientos.length === 0) {
        return (
            <div className="bg-slate-900 rounded-2xl border border-slate-800 p-10 text-center">
                <DollarSign size={40} className="mx-auto mb-3 text-slate-700" />
                <p className="text-slate-500">No hay movimientos registrados.</p>
            </div>
        );
    }

    return (
        <div className="bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden shadow-md">
            <div className="divide-y divide-slate-800">
                {/* Usamos slice().reverse() para ver el más nuevo arriba sin mutar el array original */}
                {movimientos.slice().reverse().map((m, i) => {
                    // Cálculo seguro para visualización
                    const estimadoUSD = (m.moneda === 'UYU' && exchangeRate > 0)
                        ? (m.monto / exchangeRate)
                        : null;

                    return (
                        <div key={i} className="p-4 flex justify-between items-center hover:bg-slate-800/40 transition duration-150">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-full ${m.tipo === 'ingreso' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                    {m.tipo === 'ingreso' ? <PlusCircle size={18} /> : <MinusCircle size={18} />}
                                </div>
                                <div>
                                    <p className="font-medium text-slate-200">{m.categoria}</p>
                                    <p className="text-xs text-slate-500">{m.fecha || 'Hoy'}</p>
                                </div>
                            </div>
                            <div className="text-right">
                                <p className={`font-mono font-bold text-sm ${m.tipo === 'ingreso' ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {m.tipo === 'ingreso' ? '+' : '-'}${m.monto.toLocaleString()} <span className="text-xs text-slate-500">{m.moneda}</span>
                                </p>
                                {estimadoUSD && (
                                    <p className="text-[10px] text-slate-600 font-mono mt-0.5">
                                        ≈ ${estimadoUSD.toFixed(2)} USD
                                    </p>
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};