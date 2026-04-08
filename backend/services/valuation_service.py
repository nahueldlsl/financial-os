import yfinance as yf
from datetime import datetime, timedelta
from services.cache import TTLCache
from concurrent.futures import ThreadPoolExecutor, as_completed

_val_cache = TTLCache(maxsize=100, ttl_seconds=86400)  # 24h TTL

class ValuationService:
    @staticmethod
    def evaluate_asset_fundamentals(ticker: str) -> dict:
        """Extrae métricas relativas para elaborar un Scoring o Valor Intrínseco Relativo."""
        # FIX-8b: TTLCache con eviction automática
        cached = _val_cache.get(ticker)
        if cached is not None:
            return cached

        try:
            info = yf.Ticker(ticker).info
            pe_ratio = info.get("trailingPE", 0)
            forward_pe = info.get("forwardPE", 0)
            pb_ratio = info.get("priceToBook", 0)
            # Manejar ETFs e Index Funds que carecen de 'sector' y 'country' clásico
            sector = info.get("sector")
            industry = info.get("industry", "Unknown")
            country = info.get("country")
            
            if info.get("quoteType") == "ETF":
                if not sector:
                    sector = f"ETF - {info.get('category', 'Broad Market')}"
                if not country:
                    categoria = info.get("category", "")
                    if 'World' in categoria or 'Global' in categoria or 'Emerging' in categoria:
                        country = "Global"
                    else:
                        country = "United States"
                        
            if not sector: sector = "Unknown"
            if not country: country = "Unknown"
            
            # Modelo heurístico simple de Valoración del 1 al 100
            intrinsic_score = 100
            if pe_ratio and pe_ratio > 25: intrinsic_score -= 20
            if forward_pe and pe_ratio and forward_pe > pe_ratio: intrinsic_score -= 15 # Malas proyecciones
            if pb_ratio and pb_ratio > 3: intrinsic_score -= 10
            
            result = {
                "pe_ratio": pe_ratio,
                "forward_pe": forward_pe,
                "intrinsic_score": max(0, intrinsic_score),
                "sector": sector,
                "industry": industry,
                "country": country
            }
            _val_cache.set(ticker, result)
            return result
        except Exception:
            return {
                "pe_ratio": 0, 
                "forward_pe": 0, 
                "intrinsic_score": 50, 
                "sector": "Unknown", 
                "industry": "Unknown",
                "country": "Unknown"
            } # Puntuación Neutral

    @staticmethod
    def calculate_adjusted_intrinsic_score(portfolio_assets: list, max_concentration=0.30) -> list:
        """
        El portafolio se penaliza en función a su Riesgo Sistémico.
        Si la exposición de un activo al portafolio global supera el limitante, 
        el Intrinsinc Score cae.
        
        portfolio_assets format expected:
        [{"ticker": "AAPL", "market_value": 1500.0, "intrinsic_score": 85}, ...]
        """
        total_market_value = sum([a.get("market_value", 0) for a in portfolio_assets])
        
        if total_market_value <= 0:
            return []

        adjusted_portfolio = []
        for asset in portfolio_assets:
            weight = asset.get("market_value", 0) / total_market_value
            
            # Factor de mitigación 
            concentration_penalty = 1.0
            if weight > max_concentration:
                # Si ocupa el 50%, el exceso es de 0.20
                excess = weight - max_concentration
                # Penalizamos multiplicando la distancia excedida
                concentration_penalty = max(0.2, 1.0 - (excess * 2))
                
            base_score = asset.get("intrinsic_score", 50)
            final_adjusted_score = base_score * concentration_penalty
            
            adjusted_portfolio.append({
                "ticker": asset.get("ticker", ""),
                "weight_percentage": round(weight * 100, 2),
                "risk_penalty_multiplier": round(concentration_penalty, 2),
                "adjusted_score": round(final_adjusted_score, 2),
                "original_score": base_score
            })
            
        return adjusted_portfolio

    @staticmethod
    def evaluate_assets_batch(tickers: list) -> dict:
        """FIX-9: Evalúa múltiples tickers en paralelo, respetando el caché individual."""
        results = {}
        uncached = []
        
        for t in tickers:
            cached = _val_cache.get(t)
            if cached is not None:
                results[t] = cached
            else:
                uncached.append(t)
        
        if uncached:
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {executor.submit(ValuationService.evaluate_asset_fundamentals, t): t for t in uncached}
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        results[ticker] = future.result()
                    except Exception:
                        results[ticker] = {
                            "pe_ratio": 0, "forward_pe": 0, "intrinsic_score": 50,
                            "sector": "Unknown", "industry": "Unknown", "country": "Unknown"
                        }
        
        return results
