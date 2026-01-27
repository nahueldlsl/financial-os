import React from 'react';
import { Trash2, Edit } from 'lucide-react';

export interface TradeHistoryItem {
    id: number;
    fecha: string; // ISO
    tipo: 'BUY' | 'SELL';
    cantidad: number;
    precio: number;
    total: number;
    commission: number;
}

interface HistoryTableProps {
    transactions: TradeHistoryItem[];
    onEdit: (tx: TradeHistoryItem) => void;
    onDelete: (id: number) => void;
}

const HistoryTable: React.FC<HistoryTableProps> = ({ transactions, onEdit, onDelete }) => {
    return (
        <div className="overflow-x-auto bg-gray-900/30 rounded-lg border border-gray-800">
            <table className="w-full text-left text-sm text-gray-400">
                <thead className="bg-gray-800/50 text-gray-200 border-b border-gray-700">
                    <tr>
                        <th className="py-3 px-4">Date</th>
                        <th className="py-3 px-4">Type</th>
                        <th className="py-3 px-4 text-right">Qty</th>
                        <th className="py-3 px-4 text-right">Price</th>
                        <th className="py-3 px-4 text-right">Comm.</th>
                        <th className="py-3 px-4 text-right">Total</th>
                        <th className="py-3 px-4 text-center">Actions</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                    {transactions.map((tx) => (
                        <tr key={tx.id} className="hover:bg-gray-800/50 transition-colors">
                            <td className="py-2 px-4">{new Date(tx.fecha).toLocaleDateString()}</td>
                            <td className={`py-2 px-4 font-medium ${tx.tipo === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                                {tx.tipo}
                            </td>
                            <td className="py-2 px-4 text-right">{tx.cantidad}</td>
                            <td className="py-2 px-4 text-right">${tx.precio.toFixed(2)}</td>
                            <td className="py-2 px-4 text-right">${tx.commission.toFixed(2)}</td>
                            <td className="py-2 px-4 text-right">${tx.total.toFixed(2)}</td>
                            <td className="py-2 px-4 flex justify-center gap-2">
                                <button onClick={() => onEdit(tx)} className="p-1 text-gray-500 hover:text-blue-400 transition-colors" title="Edit">
                                    <Edit size={14} />
                                </button>
                                <button
                                    onClick={() => {
                                        if (window.confirm('Are you sure you want to delete this trade? It will trigger a full history replay.')) {
                                            onDelete(tx.id);
                                        }
                                    }}
                                    className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 size={14} />
                                </button>
                            </td>
                        </tr>
                    ))}
                    {transactions.length === 0 && (
                        <tr>
                            <td colSpan={7} className="py-6 text-center text-gray-600 italic">
                                No history available.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </div>
    );
};

export default HistoryTable;
