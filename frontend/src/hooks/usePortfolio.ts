import { useState, useEffect, useCallback } from 'react';
import type { PortfolioResponse, BrokerCash, TradeAction, BrokerFund } from '../types';

// Antes tenías quizás esto fijo:
// const API_URL = 'http://localhost:8000/api';

// CAMBIAR A ESTO:
const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_URL = `${BASE_URL}/api`;

export function usePortfolio() {
    const [data, setData] = useState<PortfolioResponse | null>(null);
    const [cash, setCash] = useState<number>(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Cargar Portafolio y Caja
    const fetchAll = useCallback(async () => {
        setLoading(true);
        try {
            const [resPort, resCash] = await Promise.all([
                fetch(`${API_URL}/portfolio`),
                fetch(`${API_URL}/broker/cash`)
            ]);

            if (resPort.ok) {
                const result = await resPort.json();
                setData(result);
            }
            if (resCash.ok) {
                const cashResult: BrokerCash = await resCash.json();
                setCash(cashResult.saldo_usd);
            }
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    // Ejecutar Operación (Compra/Venta)
    const executeTrade = async (type: 'buy' | 'sell', trade: TradeAction) => {
        try {
            const res = await fetch(`${API_URL}/trade/${type}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(trade)
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Error en operación');
            }
            await fetchAll(); // Recargar datos
            return true;
        } catch (e: any) {
            alert(e.message);
            return false;
        }
    };

    // Mover Fondos (Depositar/Retirar)
    const manageCash = async (fund: BrokerFund) => {
        try {
            const res = await fetch(`${API_URL}/broker/fund`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(fund)
            });
            if (!res.ok) throw new Error('Error moviendo fondos');
            await fetchAll();
            return true;
        } catch (e: any) {
            alert(e.message);
            return false;
        }
    };

    return { data, cash, loading, error, refresh: fetchAll, executeTrade, manageCash };
}