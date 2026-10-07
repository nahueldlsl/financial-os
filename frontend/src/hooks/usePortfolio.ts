import { useState, useEffect, useCallback } from 'react';
import type { PortfolioResponse, BrokerCash, TradeAction, BrokerFund } from '../types';
import { API_URL } from '../services/api';

export function usePortfolio() {
    const [data, setData] = useState<PortfolioResponse | null>(null);
    const [cash, setCash] = useState<number>(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Cargar Portafolio y Caja
    const fetchAll = useCallback(async () => {
        setLoading(true);
        setError(null);
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        try {
            // Usamos allSettled para que un fallo en cash no rompa el portfolio y viceversa
            const results = await Promise.allSettled([
                fetch(`${API_URL}/portfolio`, { signal: controller.signal }),
                fetch(`${API_URL}/broker/cash`, { signal: controller.signal })
            ]);

            const [resPort, resCash] = results;

            // Procesar Portfolio
            if (resPort.status === 'fulfilled' && resPort.value.ok) {
                const result = await resPort.value.json();
                setData(result);
            } else if (resPort.status === 'rejected' || (resPort.status === 'fulfilled' && !resPort.value.ok)) {
                console.error("Error fetching portfolio");
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
                setError("No se pudo conectar con el servidor backend (puerto 8000).");
            } else if (resPort.status === 'rejected' || (resPort.status === 'fulfilled' && !resPort.value.ok)) {
                setError("No se pudieron cargar los datos del portafolio.");
            }

        } catch (err: any) {
            if (err.name === 'AbortError') {
                setError("El servidor demoró en responder (timeout).");
            } else {
                setError(err.message || "Error al conectar con el servidor.");
            }
        } finally {
            clearTimeout(timeoutId);
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
            // Unified Endpoint Logic
            const payload = {
                ...trade,
                type: type.toUpperCase(),
                quantity: trade.cantidad,
                price: trade.precio,
                date: trade.fecha
            };

            const res = await fetch(`${API_URL}/portfolio/trade`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
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