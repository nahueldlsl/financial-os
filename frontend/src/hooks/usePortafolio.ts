// src/hooks/usePortfolio.ts
import { useState, useEffect, useCallback } from 'react';
import type { PortfolioResponse, DripResponse } from '../types';

const API_URL = 'http://127.0.0.1:8000/api';

export function usePortfolio() {
    const [data, setData] = useState<PortfolioResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [dripLoading, setDripLoading] = useState(false);

    const fetchPortfolio = useCallback(async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_URL}/portfolio`);
            if (!res.ok) throw new Error('Error al cargar el portafolio');
            const result = await res.json();
            setData(result);
            setError(null);
        } catch (err: any) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, []);

    // Cargar al inicio
    useEffect(() => {
        fetchPortfolio();
    }, [fetchPortfolio]);

    const procesarDRIP = async (): Promise<DripResponse | null> => {
        setDripLoading(true);
        try {
            const res = await fetch(`${API_URL}/procesar-drip`, { method: 'POST' });
            const result = await res.json();

            if (!res.ok) throw new Error(result.detail || 'Error en DRIP');

            // Si hubo cambios, recargamos la data del portafolio automáticamente
            if (result.total_procesados > 0) {
                await fetchPortfolio();
            }

            return result;
        } catch (err: any) {
            alert(`Error procesando DRIP: ${err.message}`);
            return null;
        } finally {
            setDripLoading(false);
        }
    };

    return { data, loading, error, fetchPortfolio, procesarDRIP, dripLoading };
}