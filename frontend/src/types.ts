export interface Movimiento {
    tipo: 'ingreso' | 'gasto';
    monto: number;
    moneda: 'USD' | 'UYU';
    categoria: string;
    fecha?: string;
}

export interface DolarResponse {
    moneda: string;
    compra: number;
    venta: number;
    fecha: string;
    fuente: string;
}
// src/types.ts

export interface Posicion {
    Ticker: string;
    Cantidad_Total: number;
    Precio_Promedio: number;
    Precio_Actual: number;
    Valor_Mercado: number;
    Costo_Base: number;       // Nuevo (Calculado en frontend o backend)
    Ganancia_USD: number;
    Rendimiento_Porc: number;

}

export interface PortfolioResumen {
    valor_total_portafolio: number;
    ganancia_total_usd: number;
    rendimiento_total_porc: number;
}

export interface PortfolioResponse {
    resumen: PortfolioResumen;
    posiciones: Posicion[];
}

// --- NUEVOS TIPOS PARA TRADING ---
export interface BrokerCash {
    saldo_usd: number;
}

export interface TradeAction {
    ticker: string;
    cantidad: number;
    precio: number;
    fecha?: string; // ISO String
    usar_caja_broker: boolean;
    applied_fee?: number;
}

export interface BrokerFund {
    monto_enviado: number;
    monto_recibido: number;
    tipo: 'DEPOSIT' | 'WITHDRAW';
}





export interface Asset {
    id: string;
    name: string;
    category: 'Stock' | 'Cash' | 'Crypto' | 'Other';
    amount: number;
}

export interface DashboardData {
    net_worth: number;
    performance: {
        value: number;
        percentage: number;
        isPositive: boolean;
    };
    assets: Asset[];
    chart_data: {
        name: string;
        value: number;
        color: string;
    }[];
}