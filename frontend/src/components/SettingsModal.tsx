import React, { useState, useEffect } from 'react';
import { X, Save, Settings } from 'lucide-react';

interface Props {
    isOpen: boolean;
    onClose: () => void;
}

interface BrokerSettings {
    default_fee_integer: number;
    default_fee_fractional: number;
}

export const SettingsModal: React.FC<Props> = ({ isOpen, onClose }) => {
    const [settings, setSettings] = useState<BrokerSettings>({
        default_fee_integer: 0,
        default_fee_fractional: 0
    });
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    // Cargar settings al abrir
    useEffect(() => {
        if (isOpen) {
            loadSettings();
        }
    }, [isOpen]);

    const loadSettings = async () => {
        setIsLoading(true);
        try {
            const res = await fetch('http://127.0.0.1:8000/api/settings/');
            if (res.ok) {
                const data = await res.json();
                setSettings({
                    default_fee_integer: data.default_fee_integer,
                    default_fee_fractional: data.default_fee_fractional
                });
            }
        } catch (error) {
            console.error("Error loading settings:", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsSaving(true);
        try {
            const res = await fetch('http://127.0.0.1:8000/api/settings/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });
            if (res.ok) {
                onClose();
            }
        } catch (error) {
            console.error("Error saving settings:", error);
        } finally {
            setIsSaving(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <div className="bg-slate-900 border border-slate-700 w-full max-w-sm rounded-2xl shadow-2xl overflow-hidden">
                <div className="flex justify-between items-center p-4 border-b border-slate-800 bg-slate-950">
                    <h2 className="text-white font-bold flex items-center gap-2">
                        <Settings size={18} className="text-indigo-500" />
                        Configuración Broker
                    </h2>
                    <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSave} className="p-6 space-y-4">
                    {isLoading ? (
                        <div className="text-center text-slate-500 py-4">Cargando...</div>
                    ) : (
                        <>
                            <div>
                                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block">
                                    Comisión (Acción Entera)
                                </label>
                                <div className="relative">
                                    <span className="absolute left-3 top-3 text-slate-500">$</span>
                                    <input
                                        type="number" step="0.01"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 pl-7 text-white font-mono focus:border-indigo-500 outline-none transition-colors"
                                        value={settings.default_fee_integer}
                                        onChange={e => setSettings({ ...settings, default_fee_integer: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <p className="text-[10px] text-slate-600 mt-1">Se aplica cuando compras/vendes cantidades excatas (ej: 1, 5, 10)</p>
                            </div>

                            <div>
                                <label className="text-xs text-slate-400 font-bold uppercase tracking-wider mb-1 block">
                                    Comisión (Fracción)
                                </label>
                                <div className="relative">
                                    <span className="absolute left-3 top-3 text-slate-500">$</span>
                                    <input
                                        type="number" step="0.01"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 pl-7 text-white font-mono focus:border-indigo-500 outline-none transition-colors"
                                        value={settings.default_fee_fractional}
                                        onChange={e => setSettings({ ...settings, default_fee_fractional: parseFloat(e.target.value) })}
                                    />
                                </div>
                                <p className="text-[10px] text-slate-600 mt-1">Se aplica cuando operas fracciones (ej: 0.5, 1.25)</p>
                            </div>

                            <button
                                type="submit"
                                disabled={isSaving}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 transition-all mt-4"
                            >
                                <Save size={18} />
                                {isSaving ? 'Guardando...' : 'Guardar Cambios'}
                            </button>
                        </>
                    )}
                </form>
            </div>
        </div>
    );
};
