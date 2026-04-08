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

// --- ANALYTICS ---
export interface AnalyticsMetrics {
    annualized_volatility_pct: number;
    beta: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
}

export interface BenchmarkDataPoint {
    date: string;
    portfolio_value: number;
    benchmark_value: number;
}

export interface ValuationAsset {
    ticker: string;
    market_value: number;
    intrinsic_score: number;
    pe_ratio: number;
    sector: string;
    industry: string;
}

export interface ValuationAnalysis {
    ticker: string;
    weight_percentage: number;
    risk_penalty_multiplier: number;
    adjusted_score: number;
    original_score: number;
}

export interface ValuationResponse {
    analysis: ValuationAnalysis[];
    detail: ValuationAsset[];
}

// --- ORACLE AI ---
export interface OracleInsight {
    type: 'warning' | 'danger' | 'info' | 'success';
    title: string;
    message: string;
    action_suggested: string;
}

// --- PERFORMANCE BREAKDOWN ---
export interface PerformanceBreakdownData {
    invested_capital: number;
    market_value: number;
    unrealized_gain: { value: number; percentage: number };
    realized_gain: { value: number; percentage: number };
    dividends: { value: number; percentage: number };
    total_costs: { transaction_costs: number; total: number };
    total_return: { value: number; percentage: number };
    portfolio_pe: number | null;
    irr_annual: number | null;
    twr: { portfolio: number | null; sp500: number | null };
    alpha: number | null;
}