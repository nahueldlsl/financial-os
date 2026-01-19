import { useState, useEffect, useCallback } from 'react';
import type { PortfolioResponse, BrokerCash, TradeAction, BrokerFund } from '../types';

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
        setError(null);
        try {
            // Usamos allSettled para que un fallo en cash no rompa el portfolio y viceversa
            const results = await Promise.allSettled([
                fetch(`${API_URL}/portfolio`),
                fetch(`${API_URL}/broker/cash`)
            ]);

            const [resPort, resCash] = results;

            // Procesar Portfolio
            if (resPort.status === 'fulfilled' && resPort.value.ok) {
                const result = await resPort.value.json();
                setData(result);
            } else if (resPort.status === 'rejected' || (resPort.status === 'fulfilled' && !resPort.value.ok)) {
                console.error("Error fetching portfolio");
                // Podríamos setear un error específico, pero dejamos pasar si cash funcionó
            }

            // Procesar Cash
            if (resCash.status === 'fulfilled' && resCash.value.ok) {
                const cashResult: BrokerCash = await resCash.value.json();
                setCash(cashResult.saldo_usd);
            } else {
                console.error("Error fetching cash");
            }

            // Si ambos fallaron
            if (resPort.status === 'rejected' && resCash.status === 'rejected') {
                setError("No se pudo conectar con el servidor.");
            }

        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Ejecutar al montar
    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

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