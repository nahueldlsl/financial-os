import math
import yfinance as yf
import pandas as pd
import numpy as np
from services.cache import TTLCache
from services.fundamental_service import FundamentalService

# Cache con TTL de 1 hora para datos técnicos (velas diarias)
_tech_cache = TTLCache(maxsize=300, ttl_seconds=3600)
_confluence_cache = TTLCache(maxsize=300, ttl_seconds=3600)

class TechnicalService:
    @staticmethod
    def get_technical_analysis(ticker: str, force_refresh: bool = False) -> dict:
        """
        Calcula los indicadores técnicos clave a partir del histórico de precios de Yahoo Finance.
        Usa caché de 1 hora salvo force_refresh.
        """
        ticker_clean = ticker.strip().upper()
        if not force_refresh:
            cached = _tech_cache.get(ticker_clean)
            if cached is not None:
                return cached

        try:
            t = yf.Ticker(ticker_clean)
            hist = t.history(period="1y", interval="1d", auto_adjust=True)
            if hist.empty or len(hist) < 30:
                # Intentar con periodo más largo si 1y no devolvió suficiente
                hist = t.history(period="2y", interval="1d", auto_adjust=True)
            
            if hist.empty or len(hist) < 20:
                return {
                    "error": f"Datos históricos insuficientes para el análisis técnico de {ticker_clean}",
                    "ticker": ticker_clean
                }

            close = hist['Close'].dropna()
            high = hist['High'].dropna()
            low = hist['Low'].dropna()
            volume = hist['Volume'].dropna()

            current_price = float(close.iloc[-1])

            # 1. Medias Móviles Simples (SMA)
            sma_20 = float(close.rolling(window=20).mean().iloc[-1]) if len(close) >= 20 else current_price
            sma_50 = float(close.rolling(window=50).mean().iloc[-1]) if len(close) >= 50 else current_price
            sma_200 = float(close.rolling(window=200).mean().iloc[-1]) if len(close) >= 200 else current_price
            
            dist_sma_50_pct = round(((current_price - sma_50) / sma_50) * 100, 1) if sma_50 else 0.0
            dist_sma_200_pct = round(((current_price - sma_200) / sma_200) * 100, 1) if sma_200 else 0.0
            
            # Cruce Dorado / Cruce de la Muerte
            golden_cross = bool(sma_50 > sma_200) if len(close) >= 200 else False

            # 2. RSI (14 periodos)
            delta = close.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.rolling(window=14, min_periods=14).mean()
            avg_loss = loss.rolling(window=14, min_periods=14).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi_series = 100.0 - (100.0 / (1.0 + rs))
            
            last_rsi = rsi_series.dropna()
            current_rsi = round(float(last_rsi.iloc[-1]), 1) if not last_rsi.empty else 50.0

            # 3. Bandas de Bollinger (20 periodos, 2 desviaciones típicas)
            rolling_mean_20 = close.rolling(window=20).mean()
            rolling_std_20 = close.rolling(window=20).std()
            upper_band = float((rolling_mean_20 + (rolling_std_20 * 2.0)).iloc[-1])
            lower_band = float((rolling_mean_20 - (rolling_std_20 * 2.0)).iloc[-1])
            
            pct_b = (current_price - lower_band) / (upper_band - lower_band) if (upper_band > lower_band) else 0.5
            pct_b = round(min(max(pct_b, 0.0), 1.0), 2)

            # 4. MACD (12, 26, 9)
            exp1 = close.ewm(span=12, adjust=False).mean()
            exp2 = close.ewm(span=26, adjust=False).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            macd_hist = macd_line - signal_line
            
            curr_macd = round(float(macd_line.iloc[-1]), 2)
            curr_signal = round(float(signal_line.iloc[-1]), 2)
            curr_hist = round(float(macd_hist.iloc[-1]), 2)

            # 5. Soportes y Resistencias recientes (Pivot Points a 6 meses)
            recent_low_6m = float(low.tail(126).min()) if len(low) >= 126 else float(low.min())
            recent_high_6m = float(high.tail(126).max()) if len(high) >= 126 else float(high.max())

            # 6. Veredicto de Timing Técnico: ¿Cara o Barata en términos relativos de precio?
            timing_verdict, timing_label, timing_color, technical_score = TechnicalService._evaluate_timing(
                current_rsi=current_rsi,
                pct_b=pct_b,
                dist_sma_200=dist_sma_200_pct,
                current_price=current_price,
                sma_50=sma_50,
                sma_200=sma_200,
                macd_hist=curr_hist
            )

            result = {
                "ticker": ticker_clean,
                "current_price": current_price,
                "technical_score": technical_score, # 0 (extremo bajista/sobreventa) a 100 (extremo alcista/sobrecompra)
                "timing": {
                    "verdict": timing_verdict,
                    "label": timing_label,
                    "color": timing_color,
                    "action_advice": TechnicalService._get_timing_advice(timing_verdict)
                },
                "rsi": {
                    "value": current_rsi,
                    "status": "oversold" if current_rsi <= 35 else ("overbought" if current_rsi >= 70 else "neutral"),
                    "label": "Sobrevendido (Barato a corto plazo)" if current_rsi <= 35 else ("Sobrecomprado (Caro a corto plazo)" if current_rsi >= 70 else "Zona Neutral")
                },
                "moving_averages": {
                    "sma_20": round(sma_20, 2),
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2),
                    "dist_sma_50_pct": dist_sma_50_pct,
                    "dist_sma_200_pct": dist_sma_200_pct,
                    "price_above_sma_50": current_price > sma_50,
                    "price_above_sma_200": current_price > sma_200,
                    "golden_cross": golden_cross,
                    "status_label": "Cruce Dorado Alcista (SMA 50 > SMA 200)" if golden_cross else "Cruce de la Muerte Bajista (SMA 50 < SMA 200)"
                },
                "bollinger": {
                    "upper": round(upper_band, 2),
                    "lower": round(lower_band, 2),
                    "middle": round(sma_20, 2),
                    "pct_b": pct_b,
                    "status": "near_lower" if pct_b <= 0.20 else ("near_upper" if pct_b >= 0.80 else "in_band")
                },
                "macd": {
                    "line": curr_macd,
                    "signal": curr_signal,
                    "histogram": curr_hist,
                    "momentum": "bullish" if curr_hist > 0 else "bearish"
                },
                "support_resistance": {
                    "support_6m": round(recent_low_6m, 2),
                    "resistance_6m": round(recent_high_6m, 2),
                    "dist_to_support_pct": round(((current_price - recent_low_6m) / current_price) * 100, 1),
                    "dist_to_resistance_pct": round(((recent_high_6m - current_price) / current_price) * 100, 1)
                }
            }

            _tech_cache.set(ticker_clean, result)
            return result

        except Exception as e:
            return {
                "error": f"Error calculando análisis técnico para {ticker_clean}: {str(e)}",
                "ticker": ticker_clean
            }

    @staticmethod
    def _evaluate_timing(current_rsi: float, pct_b: float, dist_sma_200: float,
                         current_price: float, sma_50: float, sma_200: float, macd_hist: float):
        """Evalúa las probabilidades de timing de corto y mediano plazo."""
        # Puntuación de momentum de 0 (máxima sobreventa) a 100 (máxima sobrecompra)
        score = int(current_rsi)

        # 1. Extremo de sobreventa (precio estadísticamente barato a corto plazo)
        if current_rsi <= 35 or pct_b <= 0.15:
            return "oversold", "Sobrevendida (Barata a corto plazo / Rebote probable)", "emerald", score

        # 2. Extremo de sobrecompra (precio extendido / caro a corto plazo)
        if current_rsi >= 72 or pct_b >= 0.85 or dist_sma_200 >= 30.0:
            return "overbought", "Sobrecomprada (Cara a corto plazo / Riesgo de corrección)", "red", score

        # 3. Tendencia alcista sana
        if current_price > sma_50 and sma_50 > sma_200 and macd_hist >= 0:
            return "bullish_trend", "Tendencia Alcista Saludable (Buen Momentum)", "green", score

        # 4. Tendencia bajista activa
        if current_price < sma_50 and sma_50 < sma_200 and macd_hist <= 0:
            return "bearish_trend", "Tendencia Bajista (Presión Vendedora)", "orange", score

        return "neutral", "Zona Neutral / Consolidación", "amber", score

    @staticmethod
    def _get_timing_advice(verdict: str) -> str:
        advice = {
            "oversold": "El precio ha sufrido un castigo estadístico excesivo a corto plazo. Es una zona técnica favorable para buscar rebotes o entradas escalonadas.",
            "overbought": "El precio cotiza muy alejado de sus medias históricas con euforia compradora. No es recomendable comprar de golpe aquí; es preferible esperar una corrección táctica o tomar beneficios parciales.",
            "bullish_trend": "La estructura de precios es constructiva (por encima de sus medias de 50 y 200 días). La tendencia favorece a los compradores.",
            "bearish_trend": "El precio permanece bajo presión vendedora continua debajo de sus medias móviles clave. Comprar ahora implica asumir el riesgo de 'cuchillo cayendo' hasta confirmar suelo.",
            "neutral": "El precio se encuentra en rango lateral o fase de consolidación sin extremos técnicos de sobrecompra ni sobreventa."
        }
        return advice.get(verdict, "Monitorear acción del precio.")

    @staticmethod
    def get_confluence_analysis(ticker: str, force_refresh: bool = False) -> dict:
        """
        Sintetiza la Matriz de Confluencia:
        Análisis Fundamental (Valor Intrínseco / Calidad) + Análisis Técnico (Timing / Momentum).
        """
        ticker_clean = ticker.strip().upper()
        if not force_refresh:
            cached = _confluence_cache.get(ticker_clean)
            if cached is not None:
                return cached

        fund = FundamentalService.get_fundamentals(ticker_clean, force_refresh=force_refresh)
        tech = TechnicalService.get_technical_analysis(ticker_clean, force_refresh=force_refresh)

        if "error" in fund and "error" in tech:
            return {"error": f"No se pudo generar la confluencia para {ticker_clean}"}

        fund_summary = fund.get("summary") or {}
        fund_verdict = fund_summary.get("verdict", "neutral")
        fund_discount = fund_summary.get("discount_pct", 0.0)
        fund_fair_val = fund_summary.get("average_fair_value", 0.0)

        tech_timing = tech.get("timing") or {}
        tech_verdict = tech_timing.get("verdict", "neutral")
        tech_rsi = tech.get("rsi", {}).get("value", 50.0)

        # Matriz de Confluencia
        confluence_verdict, confluence_title, confluence_color, confluence_action = TechnicalService._synthesize_confluence(
            fund_verdict=fund_verdict,
            fund_discount=fund_discount,
            tech_verdict=tech_verdict,
            is_etf=fund.get("is_etf", False)
        )

        result = {
            "ticker": ticker_clean,
            "company_name": fund.get("company_name", ticker_clean),
            "current_price": tech.get("current_price") or fund.get("current_price", 0.0),
            "confluence": {
                "verdict_id": confluence_verdict,
                "title": confluence_title,
                "color": confluence_color,
                "action": confluence_action,
                "fundamental_summary": {
                    "label": fund_summary.get("verdict_label", "Sin datos"),
                    "fair_value": fund_fair_val,
                    "discount_pct": fund_discount,
                    "is_cheap": fund_discount >= 8.0,
                    "is_expensive": fund_discount <= -10.0
                },
                "technical_summary": {
                    "label": tech_timing.get("label", "Sin datos"),
                    "rsi": tech_rsi,
                    "is_oversold": tech_verdict == "oversold",
                    "is_overbought": tech_verdict == "overbought",
                    "trend": tech_verdict
                }
            },
            "technical_detail": tech,
            "fundamental_detail": fund
        }

        _confluence_cache.set(ticker_clean, result)
        return result

    @staticmethod
    def _synthesize_confluence(fund_verdict: str, fund_discount: float, tech_verdict: str, is_etf: bool):
        """Genera el veredicto conjunto en la matriz 2x2."""
        if is_etf:
            return (
                "etf_index",
                "ETF / Fondo Indexado",
                "blue",
                "Para este fondo indexado la decisión de inversión se fundamenta en asignación de activos a largo plazo y timing de mercado (DCA)."
            )

        # 1. Caso Ideal: Fundamentalmente barata + Técnicamente sobrevendida / en soporte
        if fund_discount >= 8.0 and tech_verdict in ["oversold", "bullish_trend"]:
            return (
                "strong_buy_confluence",
                "🎯 Compra Óptima (Máxima Confluencia)",
                "emerald",
                f"La acción cotiza con un {fund_discount}% de descuento fundamental y técnicamente se encuentra en soporte o sobreventa táctica. Excelente relación riesgo/beneficio."
            )

        # 2. Trampa de Valor: Fundamentalmente barata, pero técnicamente en caída libre
        if fund_discount >= 8.0 and tech_verdict == "bearish_trend":
            return (
                "value_trap_alert",
                "⏳ Oportunidad en Espera (Alerta de Trampa de Valor)",
                "amber",
                f"El negocio está barato ({fund_discount}% de margen de seguridad), pero la tendencia técnica sigue cayendo. Se recomienda no comprar de golpe; esperar que el gráfico confirme un suelo o realizar compras periódicas escalonadas (DCA)."
            )

        # 3. Riesgo de Corrección: Fundamentalmente cara + Técnicamente sobrecomprada
        if fund_discount <= -10.0 and tech_verdict == "overbought":
            return (
                "correction_danger",
                "🚨 Riesgo Alto de Corrección (Zona de Venta / Cautela)",
                "red",
                "La acción cotiza con fuerte sobreprecio fundamental y además el gráfico muestra sobrecompra extrema (RSI alto). Muy desaconsejado entrar ahora; riesgo elevado de caída."
            )

        # 4. Momentum Trade: Fundamentalmente exigente/cara, pero técnicamente muy alcista
        if fund_discount <= -10.0 and tech_verdict == "bullish_trend":
            return (
                "momentum_ride",
                "🏄 Impulso de Mercado (Momentum Trade)",
                "orange",
                "Por fundamentales la acción está cara, pero el mercado sigue comprando con fuerza técnica. Acompañar la subida solo con Stop Loss ceñido; no es una inversión de valor patrimonial."
            )

        # 5. En Rango / Consolidación
        return (
            "neutral_hold",
            "🟡 En Precio Justo / Consolidación",
            "slate",
            "Tanto por múltiplos fundamentales como por análisis técnico el activo cotiza en un rango de equilibrio. Mantener posición o esperar catalizadores de mercado."
        )
