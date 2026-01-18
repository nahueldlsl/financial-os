import { useState, useEffect, useMemo } from 'react';

// Assuming BrokerSettings is suitable here, or we can export it if it were in types.ts
// For now, I will define it here to match the component use, or import if I move it to types.ts.
// Since I plan to use it in TradeModal too, I will count on TradeModal importing it or redefining it?
// Best practice: Move to types.ts. But I didn't verify I can edit types.ts yet (I can, but kept it simple).
// I will just define it here and export it, or define generic interface.

export interface BrokerSettings {
    default_fee_integer: number;
    default_fee_fractional: number;
}

export const useTradeCalculator = (settings: BrokerSettings | null, initialPrice: number = 0) => {
    const [cantidad, setCantidad] = useState('');
    const [precio, setPrecio] = useState('');
    const [fee, setFee] = useState('');
    const [manualFee, setManualFee] = useState(false);
    const [mode, setMode] = useState<'buy' | 'sell'>('buy');

    // Initialize price when initialPrice changes
    useEffect(() => {
        if (initialPrice > 0) {
            setPrecio(initialPrice.toString());
        } else {
            setPrecio('');
        }
    }, [initialPrice]);

    // Auto-fill Fee logic
    useEffect(() => {
        if (!settings || manualFee) return;

        const qty = parseFloat(cantidad);
        if (isNaN(qty) || qty <= 0) {
            setFee('');
            return;
        }

        const isInteger = Number.isInteger(qty);
        // Si es entero -> integerFee, si es float -> fractionalFee
        const autoFee = isInteger ? settings.default_fee_integer : settings.default_fee_fractional;
        setFee(autoFee.toString());

    }, [cantidad, settings, manualFee]);

    // Calculation
    const totalEstimado = useMemo(() => {
        const q = parseFloat(cantidad) || 0;
        const p = parseFloat(precio) || 0;
        const f = parseFloat(fee) || 0;

        const base = q * p;
        // Buy: Cost = base + fee
        // Sell: Recibo = base - fee
        return mode === 'buy' ? (base + f) : (base - f);
    }, [cantidad, precio, fee, mode]);

    const reset = () => {
        setCantidad('');
        setFee('');
        setManualFee(false);
        // Keep mode? or reset to buy? Usually keep mode or reset.
        // Also keep price if it's from currentPrice?
    };

    return {
        cantidad, setCantidad,
        precio, setPrecio,
        fee, setFee,
        manualFee, setManualFee,
        mode, setMode,
        totalEstimado,
        reset
    };
};
