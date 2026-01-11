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
    Ganancia_USD: number;
    Rendimiento_Porc: number;
    // Agregamos opcionales por si en el futuro los muestras
    DRIP?: boolean;
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

export interface DripResponse {
    mensaje: string;
    cambios: any[];
    total_procesados: number;
}