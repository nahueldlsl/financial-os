import { useState } from 'react';
import { X, Upload, FileJson } from 'lucide-react';

interface JsonImportModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function JsonImportModal({ isOpen, onClose }: JsonImportModalProps) {
    const [jsonContent, setJsonContent] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleImport = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('http://localhost:8000/api/portfolio/import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ content: jsonContent }),
            });

            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.detail || 'Error en la importación');
            }

            const result = await response.json();
            alert(`Importación exitosa: ${result.message}`);
            onClose();
            // Recargar para ver cambios
            window.location.reload();
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-900/50">
                    <div className="flex items-center gap-3">
                        <div className="p-3 bg-indigo-500/10 rounded-xl">
                            <FileJson className="text-indigo-400" size={24} />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Importar Snapshot</h2>
                            <p className="text-sm text-slate-400">Carga masiva de activos desde JSON</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
                        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                            Pegar JSON Aquí
                        </label>
                        <textarea
                            value={jsonContent}
                            onChange={(e) => setJsonContent(e.target.value)}
                            className="w-full h-64 bg-slate-900 border border-slate-800 rounded-lg p-4 font-mono text-sm text-slate-300 focus:outline-none focus:border-indigo-500 transition resize-none placeholder:text-slate-600"
                            placeholder='[ { "Ticker": "AAPL", "Cantidad_Total": 10.5, "Precio_Promedio": 150.0 }, ... ]'
                        />
                    </div>

                    {error && (
                        <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
                            Error: {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 border-t border-slate-800 bg-slate-900/50 flex justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-slate-400 hover:text-white font-medium transition"
                    >
                        Cancelar
                    </button>
                    <button
                        onClick={handleImport}
                        disabled={loading || !jsonContent.trim()}
                        className="flex items-center gap-2 px-6 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl font-bold shadow-lg shadow-indigo-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
                    >
                        {loading ? 'Procesando...' : (
                            <>
                                <Upload size={18} />
                                Procesar Importación
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
