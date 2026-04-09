import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from services.cache import TTLCache

_risk_cache = TTLCache(maxsize=50, ttl_seconds=3600)

class RiskMetricsService:
    @staticmethod
    def fetch_historical_prices(tickers: list[str], period="1y") -> pd.DataFrame:
        """Descarga los datos históricos y retorna un DataFrame con los precios de cierre diarios."""
        if not tickers:
            return pd.DataFrame()
            
        cache_key = (tuple(sorted(tickers)), period, "prices")
        
        # FIX-8: Usar TTLCache con eviction automática
        cached = _risk_cache.get(cache_key)
        if cached is not None:
            return cached

        # Descarga en paralelo
        data = yf.download(tickers, period=period, threads=True, progress=False)["Close"]
        
        if data.empty:
            return pd.DataFrame()

        # Unificar manejo (1 ticker vs multiples)
        if isinstance(data, pd.Series):
            data = data.to_frame(name=tickers[0])
            
        data = data.ffill().dropna() # Forward-fill para manejar feriados
        
        _risk_cache.set(cache_key, data)
        return data

    @staticmethod
    def fetch_historical_returns(tickers: list[str], period="1y") -> pd.DataFrame:
        """Descarga los datos históricos y retorna un DataFrame con los retornos diarios."""
        data = RiskMetricsService.fetch_historical_prices(tickers, period)
        if data.empty:
            return pd.DataFrame()
        
        # Calcular los retornos porcentuales diarios
        returns = data.pct_change().dropna()
        return returns


    @staticmethod
    def calculate_max_drawdown(filtered_returns: pd.Series) -> float:
        """
        Función pura que recibe un array de retornos filtrados por fechas y calcula
        el Max Drawdown dinámico en esa ventana específica.
        """
        if filtered_returns.empty:
            return 0.0
        
        # 1. Pico acumulado (Running / Cumulative Max)
        cumulative_returns = (1 + filtered_returns).cumprod()
        peak = cumulative_returns.cummax()
        
        # 2. Caída diaria desde ese pico
        drawdown = (cumulative_returns - peak) / peak
        
        # 3. Valor mínimo (la caída más profunda)
        return float(drawdown.min())

    @staticmethod
    def calculate_portfolio_metrics(returns: pd.Series, market_returns: pd.Series, risk_free_rate_annual=0.04) -> dict:
        """
        Calcula estadísticas avanzadas asumiendo 'returns' como serie temporal 
        de los rendimientos diarios de la cartera consolidada y 'market_returns'
        el rendimiento del benchmark.
        """
        if returns.empty or market_returns.empty:
            return {
                "annualized_volatility_pct": 0.0,
                "beta": None,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0
            }

        # Asegurar alineación
        aligned = pd.DataFrame({"Portfolio": returns, "Market": market_returns}).dropna()
        if aligned.empty:
            return {
                "annualized_volatility_pct": 0.0,
                "beta": None,
                "sharpe_ratio": 0.0,
                "max_drawdown_pct": 0.0
            }
            
        port_ret = aligned["Portfolio"]
        mkt_ret = aligned["Market"]

        # 1. Volatilidad Anualizada
        daily_volatility = port_ret.std()
        annual_volatility = daily_volatility * np.sqrt(252)

        # 2. Beta del Portafolio
        cov_matrix = np.cov(port_ret, mkt_ret)
        beta = cov_matrix[0, 1] / cov_matrix[1, 1] if np.var(mkt_ret) > 1e-8 else 1.0

        # 3. Ratio de Sharpe
        annual_return = port_ret.mean() * 252
        sharpe_ratio = (annual_return - risk_free_rate_annual) / annual_volatility if annual_volatility > 0 else 0.0

        # 4. Maximum Drawdown calculado al vuelo de la serie ya truncada/filtrada
        max_drawdown = RiskMetricsService.calculate_max_drawdown(port_ret)

        return {
            "annualized_volatility_pct": round(float(annual_volatility * 100), 2),
            "beta": round(float(beta), 2),
            "sharpe_ratio": round(float(sharpe_ratio), 2),
            "max_drawdown_pct": round(max_drawdown * 100, 2)
        }

