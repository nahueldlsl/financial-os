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
        Anclado a base 1.0 para capturar caídas desde el primer día de observación.
        """
        if filtered_returns.empty:
            return 0.0
        
        # 1. Pico acumulado (Running / Cumulative Max anclado en 1.0)
        cum_series = (1.0 + filtered_returns).cumprod()
        cumulative_returns = pd.concat([pd.Series([1.0]), cum_series], ignore_index=True)
        peak = cumulative_returns.cummax()
        
        # 2. Caída diaria desde ese pico
        drawdown = (cumulative_returns - peak) / peak
        
        # 3. Valor mínimo (la caída más profunda)
        min_dd = float(drawdown.min())
        return min_dd if not (np.isnan(min_dd) or np.isinf(min_dd)) else 0.0

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

    @classmethod
    def calculate_for_session(cls, session, period: str = "1y") -> dict:
        """Calcula las métricas de riesgo para el portafolio en la sesión de base de datos."""
        from sqlmodel import select, func
        from models.models import Asset, TradeHistory

        assets = session.exec(select(Asset)).all()
        tickers = [asset.ticker for asset in assets if asset.cantidad_total > 0]
        if not tickers:
            return {"error": "Portafolio vacío o sin acciones."}

        inception_date = session.exec(select(func.min(TradeHistory.fecha))).first()

        portfolio_returns_df = cls.fetch_historical_returns(tickers, period=period)
        benchmark_returns_df = cls.fetch_historical_returns(["^GSPC"], period=period)

        if inception_date and not portfolio_returns_df.empty:
            inception_dt = pd.to_datetime(inception_date)
            if inception_dt.tzinfo is not None:
                inception_dt = inception_dt.tz_localize(None)
            if portfolio_returns_df.index.tz is not None:
                inception_dt = inception_dt.tz_localize(portfolio_returns_df.index.tz)

            portfolio_returns_df = portfolio_returns_df[portfolio_returns_df.index >= inception_dt]
            benchmark_returns_df = benchmark_returns_df[benchmark_returns_df.index >= inception_dt]

        if not portfolio_returns_df.empty:
            from services.market_service import MarketDataService
            prices_map = MarketDataService.get_market_prices(session, assets)
            weights_dict = {}
            total_market_val = 0.0
            for a in assets:
                if a.cantidad_total > 0 and a.ticker in portfolio_returns_df.columns:
                    mkt_val = (prices_map.get(a.ticker, 0) / 100.0) * float(a.cantidad_total)
                    weights_dict[a.ticker] = mkt_val
                    total_market_val += mkt_val

            if total_market_val > 0:
                weights = pd.Series({k: v / total_market_val for k, v in weights_dict.items()})
                weights = weights.reindex(portfolio_returns_df.columns).fillna(0)
                portfolio_weighted_returns = (portfolio_returns_df * weights).sum(axis=1)
            else:
                portfolio_weighted_returns = portfolio_returns_df.mean(axis=1)

            benchmark_1d = benchmark_returns_df.iloc[:, 0] if not benchmark_returns_df.empty else pd.Series()
            return cls.calculate_portfolio_metrics(portfolio_weighted_returns, benchmark_1d)
        else:
            return {"error": "Sin datos históricos suficientes."}


