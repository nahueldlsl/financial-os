import React, { useState } from 'react';
import { Trash2, Edit, Check, X } from 'lucide-react';

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
    onDateUpdate?: (id: number, newDate: string) => Promise<void>;
    onTradeSuccess?: () => void;
}

const HistoryTable: React.FC<HistoryTableProps> = ({ transactions, onEdit, onDelete, onDateUpdate, onTradeSuccess }) => {
    const [editingId, setEditingId] = useState<number | null>(null);
    const [tempDate, setTempDate] = useState('');

    const startEditing = (tx: TradeHistoryItem) => {
        setEditingId(tx.id);
        // Convert ISO string to "YYYY-MM-DDTHH:mm" for datetime-local input
        const d = new Date(tx.fecha);
        // Ajuste zona horaria local para input
        const localIso = new Date(d.getTime() - (d.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
        setTempDate(localIso);
    };

    const cancelEditing = () => {
        setEditingId(null);
        setTempDate('');
    };

    const saveDate = async (id: number) => {
        if (onDateUpdate && tempDate) {
            // Convert back to ISO string for backend
            const dateObj = new Date(tempDate);
            await onDateUpdate(id, dateObj.toISOString());
            setEditingId(null);
        }
    };

    const handleDelete = async (id: number) => {
        if (!window.confirm('Are you sure you want to delete this trade? It will trigger a full history replay.')) {
            return;
        }

        try {
            // Updated URL to match backend/routers/trading.py
            const response = await fetch(`/api/trading/history/${id}`, {
                method: 'DELETE',
            });

            // Handle 204 No Content (Success with no body)
            if (response.status === 204) {
                onDelete(id);
                if (onTradeSuccess) onTradeSuccess();
                return;
            }

            if (!response.ok) {
                // Try to parse error details if JSON exists
                let errorMessage = `Error ${response.status}: ${response.statusText}`;
                try {
                    const contentType = response.headers.get("content-type");
                    if (contentType && contentType.indexOf("application/json") !== -1) {
                        const errorData = await response.json();
                        if (errorData.detail) {
                            errorMessage = typeof errorData.detail === 'string' 
                                ? errorData.detail 
                                : JSON.stringify(errorData.detail, null, 2);
                        }
                    } else {
                        // Consume text body if not JSON
                        const text = await response.text();
                        if (text) errorMessage += ` - ${text}`;
                    }
                } catch (e) {
                    // Ignore parsing errors, stick to generic message
                }
                throw new Error(errorMessage);
            }

            // Success (200 OK) - consume body if present
            try {
                await response.json();
            } catch (e) {
                // Ignore if success but empty body
            }

            onDelete(id);

            if (onTradeSuccess) {
                onTradeSuccess();
            }

        } catch (error: any) {
            console.error('Error deleting transaction:', error);
            alert(error.message || 'Failed to delete transaction.');
        }
    };

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
                            <td className="py-2 px-4">
                                {editingId === tx.id ? (
                                    <div className="flex items-center gap-2">
                                        <input
                                            type="datetime-local"
                                            value={tempDate}
                                            onChange={(e) => setTempDate(e.target.value)}
                                            className="bg-gray-950 border border-gray-700 rounded p-1 text-xs text-white focus:border-indigo-500 outline-none"
                                        />
                                        <button onClick={() => saveDate(tx.id)} className="text-green-400 hover:text-green-300"><Check size={14} /></button>
                                        <button onClick={cancelEditing} className="text-red-400 hover:text-red-300"><X size={14} /></button>
                                    </div>
                                ) : (
                                    <div className="flex items-center gap-2 group">
                                        <span>{new Date(tx.fecha).toLocaleString()}</span>
                                        {onDateUpdate && (
                                            <button
                                                onClick={() => startEditing(tx)}
                                                className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-indigo-400 transition-all"
                                                title="Edit Date"
                                            >
                                                <Edit size={12} />
                                            </button>
                                        )}
                                    </div>
                                )}
                            </td>
                            <td className={`py-2 px-4 font-medium ${tx.tipo === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                                {tx.tipo}
                            </td>
                            <td className="py-2 px-4 text-right">{tx.cantidad}</td>
                            <td className="py-2 px-4 text-right">${tx.precio.toFixed(2)}</td>
                            <td className="py-2 px-4 text-right">${tx.commission.toFixed(2)}</td>
                            <td className="py-2 px-4 text-right">${tx.total.toFixed(2)}</td>
                            <td className="py-2 px-4 flex justify-center gap-2">
                                {/* Existing Edit (Price) Button - confusing to have two edits? 
                                    The prompt said "Botón Editar en cada fila... convertir celda fecha en input".
                                    I added the edit button NEXT TO THE DATE for specifically editing date, 
                                    and kept the main edit button for general edit (currently Price in AssetDetailView).
                                    I'll keep the main edit button but maybe genericize or leave as is.
                                */}
                                <button onClick={() => onEdit(tx)} className="p-1 text-gray-500 hover:text-blue-400 transition-colors" title="Edit Price/Details">
                                    <Edit size={14} />
                                </button>
                                <button
                                    onClick={() => handleDelete(tx.id)}
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
