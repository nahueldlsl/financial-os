import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface State {
    hasError: boolean;
    error?: Error;
}

/**
 * FIX-13: Error Boundary - Captura errores de renderizado de React
 * para evitar pantalla blanca fatal cuando Chart recibe NaN/Infinity.
 */
export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
    constructor(props: { children: React.ReactNode }) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error('ErrorBoundary caught:', error, info);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-200 p-8">
                    <div className="bg-slate-900 border border-red-500/30 rounded-3xl p-12 max-w-lg text-center space-y-6">
                        <div className="mx-auto w-16 h-16 rounded-full bg-red-500/10 flex items-center justify-center">
                            <AlertTriangle className="text-red-500" size={32} />
                        </div>
                        <h2 className="text-2xl font-bold text-white">Error Inesperado</h2>
                        <p className="text-slate-400 text-sm leading-relaxed">
                            Algo salió mal al renderizar los datos financieros. Esto puede ocurrir
                            si hay datos corruptos o si la API de mercado retorna valores inesperados.
                        </p>
                        <code className="block text-xs text-red-400 bg-slate-950 p-3 rounded-lg overflow-x-auto text-left">
                            {this.state.error?.message}
                        </code>
                        <button
                            onClick={() => window.location.reload()}
                            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-semibold transition-colors shadow-lg shadow-blue-600/20"
                        >
                            <RefreshCw size={16} />
                            Recargar Dashboard
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
