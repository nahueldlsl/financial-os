from datetime import datetime
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlmodel import Session, select

from models.models import Asset
from services.cache import TTLCache
from services.fundamental_service import FundamentalService
from services.technical_service import TechnicalService
from services.watchlist_service import WatchlistService
from utils.money import to_dollars

# Caché en memoria para el universo del screener (30 minutos)
_screener_cache = TTLCache(maxsize=10, ttl_seconds=1800)

# Universo curado de alta liquidez e interés global
DEFAULT_MARKET_UNIVERSE = [
    # Big Tech & AI
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
    # Value & Dividendos Defensivos
    "BRK-B", "JPM", "JNJ", "V", "PG", "UNH", "HD", "KO", "PEP", "COST",
    # Growth & Semiconductores
    "AVGO", "AMD", "PLTR", "BABA", "MELI",
    # ETFs Populares
    "SPY", "QQQ", "SCHD"
]


class ScreenerService:
    """
    Servicio con responsabilidad única (SRP):
    Orquestar la evaluación concurrente y agregación de métricas de screening
    para acciones del portafolio, watchlist y mercado global.
    """

    @staticmethod
    def _evaluate_single_ticker(
        ticker: str,
        portfolio_info: Optional[Dict],
        is_watchlist: bool,
        total_portfolio_val: float,
        force_refresh: bool = False
    ) -> Dict:
        """
        Evalúa un activo individual reuniendo datos fundamentales, técnicos y de confluencia.
        Reutiliza completamente la lógica de dominio (DRY).
        """
        clean_ticker = ticker.strip().upper()
        try:
            # 1. Obtener datos fundamentales (con caché)
            fund = FundamentalService.get_fundamentals(clean_ticker, force_refresh=force_refresh)
            # 2. Obtener datos técnicos (con caché)
            tech = TechnicalService.get_technical_analysis(clean_ticker, force_refresh=force_refresh)
            # 3. Obtener confluencia (con caché)
            conf = TechnicalService.get_confluence_analysis(clean_ticker, force_refresh=force_refresh)

            summary = fund.get("summary", {})
            metrics = fund.get("metrics", {})
            val_metrics = metrics.get("valuation", {})
            growth_div = metrics.get("growth_and_dividends", {})
            market_stats = metrics.get("market_stats", {})
            timing = tech.get("timing", {})
            rsi_data = tech.get("rsi", {})
            ma_data = tech.get("moving_averages", {})
            conf_data = conf.get("confluence", {})

            price = float(fund.get("current_price") or tech.get("current_price") or 0.0)
            margin_of_safety = float(summary.get("margin_of_safety_pct") or 0.0)
            fair_value = float(summary.get("average_fair_value") or price)
            rsi_val = float(rsi_data.get("value") or 50.0)

            # Información de portafolio si corresponde
            in_port = portfolio_info is not None
            port_shares = 0.0
            port_avg_price = 0.0
            unrealized_profit_usd = 0.0
            unrealized_profit_pct = 0.0
            port_weight_pct = 0.0

            if in_port and portfolio_info:
                port_shares = float(portfolio_info.get("cantidad", 0.0))
                port_avg_price = float(portfolio_info.get("precio_promedio", 0.0))
                if port_shares > 0:
                    market_val = port_shares * price
                    cost_val = port_shares * port_avg_price
                    unrealized_profit_usd = market_val - cost_val
                    unrealized_profit_pct = (unrealized_profit_usd / cost_val * 100.0) if cost_val > 0 else 0.0
                    port_weight_pct = (market_val / total_portfolio_val * 100.0) if total_portfolio_val > 0 else 0.0

            return {
                "ticker": clean_ticker,
                "company_name": fund.get("company_name") or clean_ticker,
                "price": round(price, 2),
                "sector": fund.get("profile", {}).get("sector") or ("ETF / Índice" if fund.get("is_etf") else "General"),
                "is_etf": bool(fund.get("is_etf", False)),
                "margin_of_safety_pct": round(margin_of_safety, 1),
                "valuation_verdict": summary.get("verdict") or "fair_value",
                "valuation_label": summary.get("verdict_label") or "En Valor Justo",
                "fair_value": round(fair_value, 2),
                "rsi": round(rsi_val, 1),
                "rsi_status": rsi_data.get("status") or "neutral",
                "rsi_label": rsi_data.get("label") or "Neutral",
                "trend": "bullish" if ma_data.get("price_above_sma_200") else "bearish",
                "golden_cross": bool(ma_data.get("golden_cross", False)),
                "confluence_verdict": conf_data.get("verdict_id") or "neutral_hold",
                "confluence_label": conf_data.get("title") or "Neutro / Mantener",
                "confluence_color": conf_data.get("color") or "slate",
                "confluence_action": conf_data.get("action") or "",
                "dividend_yield_pct": round(float(growth_div.get("dividend_yield_pct") or 0.0), 2),
                "pe_ratio": round(float(val_metrics.get("trailing_pe") or val_metrics.get("forward_pe") or 0.0), 1) if (val_metrics.get("trailing_pe") or val_metrics.get("forward_pe")) else None,
                "market_cap": market_stats.get("market_cap"),
                "in_portfolio": in_port,
                "in_watchlist": is_watchlist,
                "portfolio_shares": round(port_shares, 4) if in_port else None,
                "portfolio_avg_price": round(port_avg_price, 2) if in_port else None,
                "unrealized_profit_usd": round(unrealized_profit_usd, 2) if in_port else None,
                "unrealized_profit_pct": round(unrealized_profit_pct, 2) if in_port else None,
                "portfolio_weight_pct": round(port_weight_pct, 2) if in_port else None,
            }
        except Exception as e:
            # Fallback seguro para no romper el screener completo
            return {
                "ticker": clean_ticker,
                "company_name": clean_ticker,
                "price": 0.0,
                "sector": "Desconocido",
                "is_etf": False,
                "margin_of_safety_pct": 0.0,
                "valuation_verdict": "no_data",
                "valuation_label": "Sin Datos",
                "fair_value": 0.0,
                "rsi": 50.0,
                "rsi_status": "neutral",
                "rsi_label": "Neutral",
                "trend": "neutral",
                "golden_cross": False,
                "confluence_verdict": "neutral_hold",
                "confluence_label": "Neutro",
                "confluence_color": "slate",
                "confluence_action": "",
                "dividend_yield_pct": 0.0,
                "pe_ratio": None,
                "market_cap": None,
                "in_portfolio": portfolio_info is not None,
                "in_watchlist": is_watchlist,
                "error": str(e)
            }

    @staticmethod
    def get_screener_data(
        session: Session,
        scope: str = "all",
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        Recupera y procesa concurrentemente todos los activos del universo seleccionado.
        """
        cache_key = f"screener_all_{force_refresh}"
        cached_items = _screener_cache.get(cache_key)

        if cached_items is None or force_refresh:
            # 1. Obtener activos del portafolio del usuario
            activos_db = session.exec(select(Asset).where(Asset.cantidad_total > 0)).all()
            portfolio_map: Dict[str, Dict] = {}
            total_portfolio_val = 0.0

            for a in activos_db:
                precio_dolares = to_dollars(a.precio_promedio)
                cant = float(a.cantidad_total)
                portfolio_map[a.ticker.upper()] = {
                    "cantidad": cant,
                    "precio_promedio": precio_dolares,
                }
                # Estimación aproximada para pesos en portafolio
                cached_price = to_dollars(a.cached_price or a.precio_promedio)
                total_portfolio_val += cant * cached_price

            # 2. Obtener tickers de la watchlist
            watchlist_tickers: Set[str] = set(WatchlistService.get_watchlist_tickers(session))

            # 3. Construir universo completo deduplicado
            all_tickers_set: Set[str] = set(DEFAULT_MARKET_UNIVERSE)
            all_tickers_set.update(portfolio_map.keys())
            all_tickers_set.update(watchlist_tickers)

            ticker_list = sorted(list(all_tickers_set))

            # 4. Evaluación en paralelo usando ThreadPoolExecutor
            results: List[Dict] = []
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {
                    executor.submit(
                        ScreenerService._evaluate_single_ticker,
                        ticker,
                        portfolio_map.get(ticker),
                        ticker in watchlist_tickers,
                        total_portfolio_val,
                        force_refresh
                    ): ticker
                    for ticker in ticker_list
                }
                for future in as_completed(futures):
                    try:
                        item = future.result()
                        results.append(item)
                    except Exception:
                        pass

            # Ordenar por defecto por Margen de Seguridad desc
            results.sort(key=lambda x: x.get("margin_of_safety_pct", 0), reverse=True)
            _screener_cache.set(cache_key, results)
            cached_items = results

        # 5. Filtrar por scope solicitado
        scope = scope.lower().strip()
        if scope == "portfolio":
            return [it for it in cached_items if it.get("in_portfolio")]
        elif scope == "watchlist":
            return [it for it in cached_items if it.get("in_watchlist")]
        elif scope == "market":
            return [it for it in cached_items if not it.get("in_portfolio") or it.get("ticker") in DEFAULT_MARKET_UNIVERSE]
        
        return cached_items
