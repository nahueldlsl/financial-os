import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BrainCircuit, ArrowLeft, Zap, ShieldAlert, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { OracleInsight } from '../types';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getInsightIcon = (type: string) => {
    switch (type) {
        case 'danger': return <ShieldAlert size={24} className="text-red-500 shrink-0" />;
        case 'warning': return <AlertTriangle size={24} className="text-amber-500 shrink-0" />;
        case 'info': return <Info size={24} className="text-blue-500 shrink-0" />;
        case 'success': return <CheckCircle size={24} className="text-emerald-500 shrink-0" />;
        default: return <Zap size={24} className="text-violet-500 shrink-0" />;
    }
};

const getInsightStyles = (type: string) => {
    switch (type) {
        case 'danger': return "border-red-500/50 bg-red-500/10";
        case 'warning': return "border-amber-500/50 bg-amber-500/10";
        case 'info': return "border-blue-500/50 bg-blue-500/10";
        case 'success': return "border-emerald-500/50 bg-emerald-500/10";
        default: return "border-slate-700 bg-slate-800";
    }
};

export default function OracleView() {
    const [insights, setInsights] = useState<OracleInsight[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchOracleInsights = async () => {
            try {
                const res = await fetch(`${BASE_URL}/api/analytics/oracle`);
                if (res.ok) {
                    const data = await res.json();
                    setInsights(data.insights || []);
                }
            } catch (error) {
                console.error("Oracle fetch error:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchOracleInsights();
    }, []);

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-500 gap-4">
                <BrainCircuit className="animate-pulse text-indigo-500" size={48} />
                <span className="text-lg tracking-widest font-mono text-indigo-400">ANALIZING_PORTFOLIO_STATE...</span>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200 p-6 md:p-8 font-sans selection:bg-indigo-500/30">
            <div className="max-w-4xl mx-auto space-y-8">
                
                {/* Header */}
                <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
                    <div className="flex items-center gap-5">
                        <Link to="/" className="p-2.5 bg-slate-900 border border-slate-800 hover:border-slate-600 rounded-xl text-slate-400 hover:text-white transition-all shadow-sm">
                            <ArrowLeft size={20} />
                        </Link>
                        <div>
                            <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                                <BrainCircuit className="text-indigo-500" size={32} />
                                Oráculo Cuantitativo
                            </h1>
                            <p className="text-slate-500 text-sm mt-1">
                                Motor de análisis de riesgo y heurísticas en tiempo real.
                            </p>
                        </div>
                    </div>
                </header>

                <div className="space-y-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 mb-6">
                        <p className="text-slate-400 italic font-mono text-sm">
                            <span className="text-indigo-400 font-bold mr-2">&gt;_</span> 
                            He evaluado tus posiciones contables, el nivel de liquidez global de tu cuenta y proyectado métricas MPT (Modern Portfolio Theory). Aquí tienes mis directrices de acción automatizadas:
                        </p>
                    </div>

                    {insights.length === 0 ? (
                        <div className="text-center py-20 text-slate-500">
                            <CheckCircle className="mx-auto text-emerald-500 mb-4" size={48} />
                            <p className="text-lg font-bold">Todo en orden.</p>
                            <p>No encontré alertas críticas de riesgo o liquidez en tu estrategia actual.</p>
                        </div>
                    ) : (
                        insights.map((insight, idx) => (
                            <div 
                                key={idx} 
                                className={cn(
                                    "p-6 rounded-2xl border backdrop-blur-sm transition-all duration-300 hover:scale-[1.01] shadow-lg",
                                    getInsightStyles(insight.type)
                                )}
                            >
                                <div className="flex gap-4">
                                    {getInsightIcon(insight.type)}
                                    <div className="flex-1">
                                        <h3 className="text-lg font-bold text-white mb-2">{insight.title}</h3>
                                        <p className="text-slate-300 text-sm leading-relaxed mb-4">
                                            {insight.message}
                                        </p>
                                        <div className="bg-slate-950/50 rounded-xl p-4 border border-white/5">
                                            <div className="flex items-start gap-2">
                                                <Zap size={16} className="text-yellow-500 mt-0.5 shrink-0" />
                                                <div>
                                                    <span className="text-xs uppercase tracking-widest text-slate-500 font-bold mb-1 block">Acción Sugerida</span>
                                                    <p className="text-sm font-medium text-slate-200">
                                                        {insight.action_suggested}
                                                    </p>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                </div>

            </div>
        </div>
    );
}
