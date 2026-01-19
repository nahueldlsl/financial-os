import React from 'react';
import { formatCurrency } from '../utils/format';

interface Props {
    balance: number;
    isLoading: boolean;
}

export const BalanceCard: React.FC<Props> = ({ balance, isLoading }) => {
    // Si es NaN o está cargando, mostramos un estado seguro
    const displayBalance = (isNaN(balance) || isLoading) ? 0 : balance;

    return (
        <div className="bg-gradient-to-br from-indigo-900 to-slate-900 p-6 rounded-2xl border border-indigo-500/30 text-center shadow-lg shadow-indigo-500/10">
            <p className="text-indigo-200 text-sm mb-2 font-medium tracking-wide">
                DISPONIBLE REAL (ESTIMADO)
            </p>
            <h2 className="text-4xl font-bold text-white flex justify-center items-end gap-2">
                {isLoading ? (
                    <span className="animate-pulse text-slate-500">---</span>
                ) : (
                    <>
                        {formatCurrency(displayBalance)}
                        <span className="text-lg text-indigo-300 mb-1">USD</span>
                    </>
                )}
            </h2>
        </div>
    );
};