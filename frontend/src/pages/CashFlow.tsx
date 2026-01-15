import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom'; // Asegúrate de tener react-router-dom instalado
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { BalanceCard } from '../components/BalanceCard';
import { TransactionForm } from '../components/TransactionForm';
import { TransactionList } from '../components/TransactionList.tsx';
import type { Movimiento, DolarResponse } from '../types';

// Antes tenías quizás esto fijo:
// const API_URL = 'http://localhost:8000/api';

// CAMBIAR A ESTO:
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_BASE = `${BASE_URL}/api`;

export default function CashFlow() {
    // Estado
    const [exchangeRate, setExchangeRate] = useState<number>(0);
    const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [lastUpdate, setLastUpdate] = useState<string>('');

    // Carga inicial
    useEffect(() => {
        cargarDatos();
    }, []);

    const cargarDatos = async () => {
        setLoading(true);
        try {
            // Hacemos las peticiones en paralelo
            const [resDolar, resMovs] = await Promise.all([
                fetch(`${API_BASE}/dolar-uy`),
                fetch(`${API_BASE}/movimientos`)
            ]);

            if (resDolar.ok) {
                const dataDolar: DolarResponse = await resDolar.json();
                // Usamos la cotización de VENTA (el precio más alto/conservador)
                // Si la API falla y devuelve null, usamos 1 para evitar división por cero
                setExchangeRate(dataDolar.venta || dataDolar.compra || 0);

                // Formateamos la hora para mostrarla
                const fecha = new Date(dataDolar.fecha || Date.now());
                setLastUpdate(fecha.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
            }

            if (resMovs.ok) {
                const dataMovs: Movimiento[] = await resMovs.json();
                setMovimientos(dataMovs);
            }

        } catch (error) {
            console.error("Error cargando datos:", error);
        } finally {
            setLoading(false);
        }
    };

    // Lógica para guardar
    const handleSaveMovimiento = async (nuevoMov: Movimiento) => {
        try {
            const res = await fetch(`${API_BASE}/movimientos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(nuevoMov)
            });

            if (res.ok) {
                // Opción A: Recargar todo (más seguro, menos eficiente)
                await cargarDatos();

                // Opción B (Optimista): Agregar localmente para que sea instantáneo
                // const savedMov = await res.json();
                // setMovimientos([...movimientos, savedMov.movimiento]);
            }
        } catch (error) {
            console.error("Error guardando:", error);
            alert("No se pudo conectar con el servidor.");
        }
    };

    // Lógica financiera (evitando NaN)
    const calcularBalanceTotal = (): number => {
        if (!exchangeRate || exchangeRate === 0) return 0;

        return movimientos.reduce((total, m) => {
            // Normalizar todo a USD
            let valorEnUSD = 0;

            if (m.moneda === 'UYU') {
                valorEnUSD = m.monto / exchangeRate;
            } else {
                valorEnUSD = m.monto;
            }

            return m.tipo === 'ingreso'
                ? total + valorEnUSD
                : total - valorEnUSD;
        }, 0);
    };

    return (
        <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8 font-sans">
            {/* Header */}
            <header className="max-w-5xl mx-auto mb-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                    <Link to="/" className="p-2.5 bg-slate-800 rounded-xl hover:bg-slate-700 transition text-slate-300">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold tracking-tight">Billetera Inteligente</h1>
                        <p className="text-slate-500 text-xs">Gestión financiera personal</p>
                    </div>
                </div>

                <div className="flex items-center gap-3 bg-slate-900 px-5 py-2.5 rounded-full border border-slate-800 shadow-sm self-start sm:self-auto">
                    <div className="flex flex-col items-end leading-tight">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Dólar Venta</span>
                        <span className="font-mono text-emerald-400 font-bold text-lg">
                            ${exchangeRate > 0 ? exchangeRate : '--'}
                        </span>
                    </div>
                    <div className="h-8 w-px bg-slate-800 mx-1"></div>
                    <button
                        onClick={cargarDatos}
                        disabled={loading}
                        className={`p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-full transition ${loading ? 'animate-spin' : ''}`}
                        title={`Actualizado: ${lastUpdate}`}
                    >
                        <RefreshCw size={18} />
                    </button>
                </div>
            </header>

            {/* Grid Principal */}
            <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-12 gap-6">

                {/* Columna Izquierda (Balance y Formulario) - Ocupa 4 columnas en desktop */}
                <div className="md:col-span-4 space-y-6">
                    <BalanceCard
                        balance={calcularBalanceTotal()}
                        isLoading={loading}
                    />
                    <TransactionForm onSave={handleSaveMovimiento} />
                </div>

                {/* Columna Derecha (Lista) - Ocupa 8 columnas en desktop */}
                <div className="md:col-span-8 space-y-4">
                    <div className="flex justify-between items-end px-1">
                        <h3 className="text-lg font-semibold text-slate-300">Últimos Movimientos</h3>
                        <span className="text-xs text-slate-500">{movimientos.length} registros</span>
                    </div>

                    <TransactionList
                        movimientos={movimientos}
                        exchangeRate={exchangeRate}
                    />
                </div>

            </div>
        </div>
    );
}