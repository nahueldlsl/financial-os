import React from 'react';
import type { Posicion } from '../../types';
import { Badge } from '../ui/Badge';

interface Props {
    posiciones: Posicion[];
}

export const PortfolioTable: React.FC<Props> = ({ posiciones }) => {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-800/50 text-slate-400 uppercase text-xs tracking-wider">
                            <th className="p-4 font-semibold">Ticker</th>
                            <th className="p-4 font-semibold text-right">Cantidad</th>
                            <th className="p-4 font-semibold text-right">Precio Prom.</th>
                            <th className="p-4 font-semibold text-right">Precio Actual</th>
                            <th className="p-4 font-semibold text-right">Valor Total</th>
                            <th className="p-4 font-semibold text-right">P/L ($)</th>
                            <th className="p-4 font-semibold text-center">P/L (%)</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {posiciones.map((accion) => (
                            <tr key={accion.Ticker} className="hover:bg-slate-800/30 transition-colors group">
                                <td className="p-4 font-bold text-indigo-400 group-hover:text-indigo-300 transition">
                                    {accion.Ticker}
                                </td>
                                <td className="p-4 text-slate-300 text-right">{accion.Cantidad_Total.toFixed(4)}</td>
                                <td className="p-4 text-slate-400 text-right">${accion.Precio_Promedio.toFixed(2)}</td>
                                <td className="p-4 text-slate-200 text-right">${accion.Precio_Actual.toFixed(2)}</td>
                                <td className="p-4 font-bold text-white text-right">${accion.Valor_Mercado.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                                <td className={`p-4 font-medium text-right ${accion.Ganancia_USD >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                    {accion.Ganancia_USD >= 0 ? '+' : ''}{accion.Ganancia_USD.toFixed(2)}
                                </td>
                                <td className="p-4 text-center">
                                    <Badge value={accion.Rendimiento_Porc} />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};