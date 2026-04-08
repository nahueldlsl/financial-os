import { useState } from 'react';
import { X, Upload, FileJson } from 'lucide-react';

interface JsonImportModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export function JsonImportModal({ isOpen, onClose }: JsonImportModalProps) {
    const [historialFile, setHistorialFile] = useState<File | null>(null);
    const [posicionesFile, setPosicionesFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen) return null;

    const handleImport = async () => {
        if (!historialFile || !posicionesFile) {
            setError("Debes subir ambos archivos JSON");
            return;
        }
        
        setLoading(true);
        setError(null);
        try {
            const formData = new FormData();
            formData.append('historial_file', historialFile);
            formData.append('posiciones_file', posicionesFile);

            const response = await fetch('http://localhost:8000/api/data/import-broker', {
                method: 'POST',
                body: formData,
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
                            Archivo historial_transacciones.json
                        </label>
                        <input
                            type="file"
                            accept=".json"
                            onChange={(e) => setHistorialFile(e.target.files ? e.target.files[0] : null)}
                            className="w-full text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-indigo-500/20 file:text-indigo-400 hover:file:bg-indigo-500/30 transition-colors"
                        />
                    </div>
                    
                    <div className="bg-slate-950 rounded-xl border border-slate-800 p-4">
                        <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                            Archivo posiciones_actuales.json
                        </label>
                        <input
                            type="file"
                            accept=".json"
                            onChange={(e) => setPosicionesFile(e.target.files ? e.target.files[0] : null)}
                            className="w-full text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-indigo-500/20 file:text-indigo-400 hover:file:bg-indigo-500/30 transition-colors"
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
                        disabled={loading || !historialFile || !posicionesFile}
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
