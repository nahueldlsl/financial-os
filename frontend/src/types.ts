export interface Movimiento {
    id?: number;
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

// --- FUNDAMENTAL ANALYSIS & INTRINSIC VALUATION ---
export interface ValuationModelAssumption {
    [key: string]: string | number | null | undefined;
}

export interface ValuationModelItem {
    id: string;
    name: string;
    value: number;
    weight: number;
    diff_pct: number;
    description: string;
    assumptions: Record<string, string | number>;
    is_outlier?: boolean;
    outlier_reason?: string;
}

export interface ValuationSummaryData {
    average_fair_value: number;
    min_fair_value: number;
    max_fair_value: number;
    current_price: number;
    discount_pct: number;
    margin_of_safety_pct: number;
    verdict: 'deeply_undervalued' | 'undervalued' | 'fair_value' | 'overvalued' | 'deeply_overvalued' | 'etf_index' | 'no_data';
    verdict_label: string;
    verdict_color: 'emerald' | 'green' | 'amber' | 'orange' | 'red' | 'blue' | 'gray';
    models_count: number;
    etf_note?: string;
}

export interface FundamentalMetricsData {
    valuation: {
        trailing_pe?: number | null;
        forward_pe?: number | null;
        peg_ratio?: number | null;
        price_to_book?: number | null;
        price_to_sales?: number | null;
        ev_to_ebitda?: number | null;
        ev_to_revenue?: number | null;
        nav_price?: number | null;
        nav_premium_discount_pct?: number | null;
    };
    profitability: {
        profit_margin_pct?: number | null;
        operating_margin_pct?: number | null;
        gross_margin_pct?: number | null;
        return_on_equity_pct?: number | null;
        return_on_assets_pct?: number | null;
    };
    health: {
        debt_to_equity?: number | null;
        current_ratio?: number | null;
        quick_ratio?: number | null;
        total_cash?: number | null;
        total_debt?: number | null;
        free_cash_flow?: number | null;
        operating_cash_flow?: number | null;
        total_assets?: number | null;
    };
    growth_and_dividends: {
        revenue_growth_yoy_pct?: number | null;
        earnings_growth_yoy_pct?: number | null;
        dividend_yield_pct?: number | null;
        dividend_rate?: number | null;
        payout_ratio_pct?: number | null;
    };
    market_stats: {
        market_cap?: number | null;
        enterprise_value?: number | null;
        beta?: number | null;
        fifty_two_week_low?: number | null;
        fifty_two_week_high?: number | null;
        range_position_pct?: number | null;
        shares_outstanding?: number | null;
    };
}

export interface CompanyProfileData {
    sector: string;
    industry: string;
    country: string;
    website: string;
    description: string;
}

export interface FundamentalAnalysisResponse {
    ticker: string;
    company_name: string;
    is_etf: boolean;
    current_price: number;
    summary: ValuationSummaryData;
    models: ValuationModelItem[];
    metrics: FundamentalMetricsData;
    profile: CompanyProfileData;
    error?: string;
}

// --- TECHNICAL ANALYSIS & CONFLUENCE ---
export interface TechnicalAnalysisResponse {
    ticker: string;
    current_price: number;
    technical_score: number;
    timing: {
        verdict: 'oversold' | 'overbought' | 'bullish_trend' | 'bearish_trend' | 'neutral';
        label: string;
        color: 'emerald' | 'green' | 'amber' | 'orange' | 'red';
        action_advice: string;
    };
    rsi: {
        value: number;
        status: 'oversold' | 'overbought' | 'neutral';
        label: string;
    };
    moving_averages: {
        sma_20: number;
        sma_50: number;
        sma_200: number;
        dist_sma_50_pct: number;
        dist_sma_200_pct: number;
        price_above_sma_50: boolean;
        price_above_sma_200: boolean;
        golden_cross: boolean;
        status_label: string;
    };
    bollinger: {
        upper: number;
        lower: number;
        middle: number;
        pct_b: number;
        status: string;
    };
    macd: {
        line: number;
        signal: number;
        histogram: number;
        momentum: 'bullish' | 'bearish';
    };
    support_resistance: {
        support_6m: number;
        resistance_6m: number;
        dist_to_support_pct: number;
        dist_to_resistance_pct: number;
    };
    error?: string;
}

export interface ConfluenceResponse {
    ticker: string;
    company_name: string;
    current_price: number;
    confluence: {
        verdict_id: 'strong_buy_confluence' | 'value_trap_alert' | 'correction_danger' | 'momentum_ride' | 'neutral_hold' | 'etf_index';
        title: string;
        color: 'emerald' | 'green' | 'amber' | 'orange' | 'red' | 'blue' | 'slate';
        action: string;
        fundamental_summary: {
            label: string;
            fair_value: number;
            discount_pct: number;
            is_cheap: boolean;
            is_expensive: boolean;
        };
        technical_summary: {
            label: string;
            rsi: number;
            is_oversold: boolean;
            is_overbought: boolean;
            trend: string;
        };
    };
    technical_detail: TechnicalAnalysisResponse;
    fundamental_detail: FundamentalAnalysisResponse;
    error?: string;
}

// --- SEARCH & EXPLORATION ---
export interface SearchAssetResult {
    symbol: string;
    name: string;
    exchange: string;
    type: string;
    sector?: string;
}

// --- STOCK SCREENER & RADAR ---
export type ScreenerScope = 'all' | 'portfolio' | 'watchlist' | 'market';

export interface ScreenerItem {
    ticker: string;
    company_name: string;
    price: number;
    sector: string;
    is_etf: boolean;
    margin_of_safety_pct: number;
    valuation_verdict: string;
    valuation_label: string;
    fair_value: number;
    rsi: number;
    rsi_status: 'oversold' | 'neutral' | 'overbought';
    rsi_label: string;
    trend: 'bullish' | 'bearish' | 'neutral';
    golden_cross: boolean;
    confluence_verdict: string;
    confluence_label: string;
    confluence_color: 'emerald' | 'green' | 'amber' | 'orange' | 'red' | 'blue' | 'slate';
    confluence_action: string;
    dividend_yield_pct: number;
    pe_ratio: number | null;
    market_cap: number | null;
    in_portfolio: boolean;
    in_watchlist: boolean;
    portfolio_shares?: number | null;
    portfolio_avg_price?: number | null;
    unrealized_profit_usd?: number | null;
    unrealized_profit_pct?: number | null;
    portfolio_weight_pct?: number | null;
    error?: string;
}

export interface ScreenerFilters {
    search: string;
    scope: ScreenerScope;
    valuationStatus: 'all' | 'undervalued' | 'fair_value' | 'overvalued';
    minMarginOfSafety: number | null; // e.g., 0, 15, 20
    rsiStatus: 'all' | 'oversold' | 'neutral' | 'overbought';
    onlyGoldenCross: boolean;
    confluenceVerdict: 'all' | 'strong_buy_confluence' | 'value_trap_alert' | 'correction_danger' | 'momentum_ride';
    sector: string;
    assetType: 'all' | 'equity' | 'etf';
    portfolioProfitStatus: 'all' | 'gainers' | 'losers';
    minDividendYield?: number | null;
}

export interface ScreenerPreset {
    id: string;
    label: string;
    icon: string;
    description: string;
    filters: Partial<ScreenerFilters>;
}

export interface ScreenerResponse {
    scope: string;
    total_items: number;
    items: ScreenerItem[];
}

export interface WatchlistResponse {
    watchlist: string[];
    items: {
        id: number;
        ticker: string;
        added_at: string;
        notes?: string | null;
    }[];
}


