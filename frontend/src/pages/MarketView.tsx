import { useState, useEffect } from 'react';
import { ArrowLeft, TrendingUp, TrendingDown } from 'lucide-react';
import { Link } from 'react-router-dom';

// Interfaces (Tipos de datos)
interface Posicion {
    Ticker: string;
    Cantidad_Total: number;
    Precio_Promedio: number;
    Precio_Actual: number;
    Valor_Mercado: number;
    Ganancia_USD: number;
    Rendimiento_Porc: number;
}

interface PortfolioData {
    resumen: {
        valor_total_portafolio: number;
        ganancia_total_usd: number;
        rendimiento_total_porc: number;
    };
    posiciones: Posicion[];
}

export default function MarketView() {
    const [data, setData] = useState<PortfolioData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetch('http://127.0.0.1:8000/api/portfolio')
            .then(res => {
                if (!res.ok) throw new Error('Error conectando al servidor');
                return res.json();
            })
            .then(setData)
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    if (error) return <div className="p-10 text-red-500 text-center">Error: {error}</div>;
    if (!data && loading) return <div className="p-10 text-slate-400 text-center animate-pulse">Cargando mercado...</div>;

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-10">
            {/* Header con Botón de Volver */}
            <header className="max-w-7xl mx-auto mb-8 flex items-center gap-4">
                <Link to="/" className="p-2 bg-slate-800 rounded-lg hover:bg-slate-700 transition">
                    <ArrowLeft size={20} />
                </Link>
                <div>
                    <h1 className="text-3xl font-bold text-white">Mercado de Valores</h1>
                    <p className="text-slate-400 text-sm">Tus posiciones en tiempo real (Hapi + Yahoo Finance)</p>
                </div>
            </header>

            {/* Tarjetas de Resumen Superior */}
            <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
                    <p className="text-slate-400 text-sm font-medium">Valor Total</p>
                    <p className="text-3xl font-bold mt-2">${data?.resumen.valor_total_portafolio.toLocaleString()}</p>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
                    <p className="text-slate-400 text-sm font-medium">Ganancia Neta</p>
                    <div className={`flex items-center gap-2 mt-2 text-3xl font-bold ${data?.resumen.ganancia_total_usd! >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data?.resumen.ganancia_total_usd! >= 0 ? '+' : ''}
                        ${data?.resumen.ganancia_total_usd}
                    </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
                    <p className="text-slate-400 text-sm font-medium">Rendimiento Total</p>
                    <div className={`flex items-center gap-2 mt-2 text-3xl font-bold ${data?.resumen.rendimiento_total_porc! >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {data?.resumen.rendimiento_total_porc! >= 0 ? <TrendingUp size={28} /> : <TrendingDown size={28} />}
                        {data?.resumen.rendimiento_total_porc}%
                    </div>
                </div>
            </div>

            {/* Tabla Principal */}
            <div className="max-w-7xl mx-auto bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-slate-800/50 text-slate-400 uppercase text-xs tracking-wider">
                                <th className="p-4 font-semibold">Ticker</th>
                                <th className="p-4 font-semibold">Cantidad</th>
                                <th className="p-4 font-semibold">Precio Prom.</th>
                                <th className="p-4 font-semibold">Precio Actual</th>
                                <th className="p-4 font-semibold">Valor Total</th>
                                <th className="p-4 font-semibold">P/L ($)</th>
                                <th className="p-4 font-semibold">P/L (%)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {data?.posiciones.map((accion) => (
                                <tr key={accion.Ticker} className="hover:bg-slate-800/30 transition-colors">
                                    <td className="p-4 font-bold text-blue-400">{accion.Ticker}</td>
                                    <td className="p-4 text-slate-300">{accion.Cantidad_Total}</td>
                                    <td className="p-4 text-slate-400">${accion.Precio_Promedio.toFixed(2)}</td>
                                    <td className="p-4 text-slate-200">${accion.Precio_Actual.toFixed(2)}</td>
                                    <td className="p-4 font-bold text-white">${accion.Valor_Mercado.toLocaleString()}</td>
                                    <td className={`p-4 font-medium ${accion.Ganancia_USD >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                        {accion.Ganancia_USD >= 0 ? '+' : ''}{accion.Ganancia_USD}
                                    </td>
                                    <td className="p-4">
                                        <span className={`px-2 py-1 rounded text-xs font-bold ${accion.Rendimiento_Porc >= 0
                                                ? 'bg-emerald-500/10 text-emerald-400'
                                                : 'bg-red-500/10 text-red-400'
                                            }`}>
                                            {accion.Rendimiento_Porc}%
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}