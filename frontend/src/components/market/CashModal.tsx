import React, { useState, useEffect } from 'react';
import { X, ArrowRightLeft } from 'lucide-react';
import type { BrokerFund } from '../../types';

interface Props {
    isOpen: boolean;
    onClose: () => void;
    currentBalance: number;
    onSubmit: (fund: BrokerFund) => Promise<boolean>;
}

export const CashModal: React.FC<Props> = ({ isOpen, onClose, currentBalance, onSubmit }) => {
    const [enviado, setEnviado] = useState('');
    const [recibido, setRecibido] = useState('');
    const [tipo, setTipo] = useState<'DEPOSIT' | 'WITHDRAW'>('DEPOSIT');

    // Auto-llenar recibido al escribir enviado (asumiendo 0 comisión al inicio)
    useEffect(() => {
        if (enviado && !recibido) setRecibido(enviado);
    }, [enviado]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const success = await onSubmit({
            monto_enviado: parseFloat(enviado),
            monto_recibido: parseFloat(recibido),
            tipo
        });
        if (success) {
            setEnviado(''); setRecibido(''); onClose();
        }
    };

    const comision = (parseFloat(enviado || '0') - parseFloat(recibido || '0'));

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 w-full max-w-sm rounded-2xl shadow-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-xl font-bold text-white">Gestión de Caja</h3>
                    <button onClick={onClose}><X className="text-slate-400 hover:text-white" /></button>
                </div>

                {/* Switch Tipo */}
                <div className="flex bg-slate-950 p-1 rounded-lg mb-6">
                    <button onClick={() => setTipo('DEPOSIT')} className={`flex-1 py-2 rounded-md font-bold text-sm transition ${tipo === 'DEPOSIT' ? 'bg-indigo-600 text-white' : 'text-slate-500'}`}>DEPOSITAR</button>
                    <button onClick={() => setTipo('WITHDRAW')} className={`flex-1 py-2 rounded-md font-bold text-sm transition ${tipo === 'WITHDRAW' ? 'bg-indigo-600 text-white' : 'text-slate-500'}`}>RETIRAR</button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="text-xs text-slate-500 font-bold uppercase">Monto {tipo === 'DEPOSIT' ? 'a Enviar (Banco)' : 'a Retirar (Broker)'}</label>
                        <input
                            type="number" step="0.01"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-indigo-500 outline-none"
                            value={enviado} onChange={e => setEnviado(e.target.value)}
                        />
                    </div>

                    <div className="flex justify-center text-slate-600"><ArrowRightLeft size={16} /></div>

                    <div>
                        <label className="text-xs text-slate-500 font-bold uppercase">Monto {tipo === 'DEPOSIT' ? 'Recibido (Broker)' : 'Recibido (Banco)'}</label>
                        <input
                            type="number" step="0.01"
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-white focus:border-indigo-500 outline-none"
                            value={recibido} onChange={e => setRecibido(e.target.value)}
                        />
                    </div>

                    {comision > 0 && (
                        <div className="bg-red-500/10 border border-red-500/20 p-2 rounded text-center">
                            <p className="text-xs text-red-400">Comisión estimada: <strong>${comision.toFixed(2)}</strong></p>
                            <p className="text-[10px] text-slate-500">Se registrará como gasto automáticamente.</p>
                        </div>
                    )}

                    <button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg mt-2">
                        CONFIRMAR {tipo === 'DEPOSIT' ? 'DEPÓSITO' : 'RETIRO'}
                    </button>
                </form>
            </div>
        </div>
    );
};