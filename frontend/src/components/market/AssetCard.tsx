import React, { useState } from 'react'; // Agregar useState
import { TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react';
import type { Posicion } from '../../types';

interface Props {
    asset: Posicion;
    totalPortfolioValue: number;
    onClick: () => void;
}

export const AssetCard: React.FC<Props> = ({ asset, totalPortfolioValue, onClick }) => {
    const allocation = totalPortfolioValue > 0
        ? (asset.Valor_Mercado / totalPortfolioValue) * 100
        : 0;

    const isProfitable = asset.Ganancia_USD >= 0;
    const [imgError, setImgError] = useState(false);

    // URL del Logo (Parqet es un CDN gratuito para finanzas)
    const logoUrl = `https://assets.parqet.com/logos/symbol/${asset.Ticker}?format=png`;

    return (
        <div
            onClick={onClick}
            className="group cursor-pointer bg-slate-900 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/50 rounded-2xl p-5 transition-all duration-300 relative overflow-hidden"
        >
            <div className={`absolute inset-0 opacity-0 group-hover:opacity-5 transition-opacity ${isProfitable ? 'bg-emerald-500' : 'bg-red-500'}`} />

            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-3">
                    {/* LOGO */}
                    <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center overflow-hidden border border-slate-700">
                        {!imgError ? (
                            <img
                                src={logoUrl}
                                alt={asset.Ticker}
                                className="w-full h-full object-cover"
                                onError={() => setImgError(true)}
                            />
                        ) : (
                            <span className="text-xs font-bold text-slate-400">{asset.Ticker.substring(0, 2)}</span>
                        )}
                    </div>
                    <div>
                        <h3 className="text-xl font-bold text-white tracking-tight leading-none">{asset.Ticker}</h3>
                        <p className="text-[10px] text-slate-500 font-medium mt-1">
                            {asset.Cantidad_Total.toFixed(4)} accs
                        </p>
                    </div>
                </div>

                {/* Badge Rentabilidad */}
                <div className={`flex flex-col items-end ${isProfitable ? 'text-emerald-400' : 'text-red-400'}`}>
                    <span className="text-lg font-bold flex items-center gap-1">
                        {isProfitable ? <TrendingUp size={18} /> : <TrendingDown size={18} />}
                        {asset.Rendimiento_Porc}%
                    </span>
                    <span className="text-xs opacity-80 font-mono">
                        {isProfitable ? '+' : ''}${asset.Ganancia_USD.toLocaleString()}
                    </span>
                </div>
            </div>

            {/* ... Resto de Métricas (igual que antes) ... */}
            <div className="grid grid-cols-2 gap-4 mt-2">
                <div className="bg-slate-950/50 p-2 rounded-lg">
                    <div className="flex items-center gap-1.5 text-slate-400 text-[10px] uppercase font-bold tracking-wider mb-0.5">
                        <DollarSign size={10} /> Valor Actual
                    </div>
                    <p className="text-white font-mono font-semibold">
                        ${asset.Valor_Mercado.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                </div>

                <div className="bg-slate-950/50 p-2 rounded-lg">
                    <div className="flex items-center gap-1.5 text-slate-400 text-[10px] uppercase font-bold tracking-wider mb-0.5">
                        <PieChart size={10} /> Portafolio
                    </div>
                    <div className="flex items-center gap-2">
                        <p className="text-white font-mono font-semibold">
                            {allocation.toFixed(1)}%
                        </p>
                        <div className="h-1.5 w-10 bg-slate-800 rounded-full overflow-hidden">
                            <div className="h-full bg-indigo-500" style={{ width: `${Math.min(allocation, 100)}%` }}></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};