import math
import yfinance as yf
from services.cache import TTLCache

# Cache con TTL de 12 horas para balances y datos fundamentales
_fundamental_cache = TTLCache(maxsize=300, ttl_seconds=43200)

class FundamentalService:
    @staticmethod
    def get_fundamentals(ticker: str, force_refresh: bool = False) -> dict:
        """
        Obtiene los datos fundamentales completos y calcula los modelos de valor intrínseco.
        Usa caché en memoria de 12 horas salvo que se solicite force_refresh.
        """
        ticker_clean = ticker.strip().upper()
        
        if not force_refresh:
            cached = _fundamental_cache.get(ticker_clean)
            if cached is not None:
                return cached

        try:
            t = yf.Ticker(ticker_clean)
            info = t.info or {}
        except Exception as e:
            return {
                "error": f"No se pudieron obtener datos de mercado para {ticker_clean}: {str(e)}",
                "ticker": ticker_clean
            }

        quote_type = info.get("quoteType", "EQUITY")
        current_price = float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0)

        # Si es un ETF o Fondo Indexado
        if quote_type == "ETF":
            result = FundamentalService._build_etf_response(ticker_clean, current_price, info)
            _fundamental_cache.set(ticker_clean, result)
            return result

        # Extracción y limpieza de métricas clave
        eps = float(info.get("trailingEps") or 0.0)
        forward_eps = float(info.get("forwardEps") or eps)
        bvps = float(info.get("bookValue") or 0.0)
        fcf = float(info.get("freeCashflow") or 0.0)
        operating_cf = float(info.get("operatingCashflow") or 0.0)
        shares = float(info.get("sharesOutstanding") or 0.0)
        beta = float(info.get("beta") or 1.0)
        ebitda = float(info.get("ebitda") or 0.0)
        total_cash = float(info.get("totalCash") or 0.0)
        total_debt = float(info.get("totalDebt") or 0.0)
        market_cap = float(info.get("marketCap") or 0.0)
        sector = str(info.get("sector") or "").strip()
        is_financial = sector.lower() in ["financial services", "financials"]
        
        # 1. Normalización de Acciones Totales Diluidas (Evita desajustes en conglomerados con acciones duales)
        effective_shares = shares
        if market_cap > 0 and current_price > 0:
            implied_shares = market_cap / current_price
            if implied_shares > shares * 1.15:
                effective_shares = implied_shares

        # 2. Normalización de Valor Libro (Dual-Class Shares: e.g. BRK.A vs BRK.B)
        price_to_book_raw = info.get("priceToBook")
        if ticker_clean in ["BRK-B", "BRK.B"]:
            # Berkshire Hathaway: 1 acción Clase A equivale a 1,500 acciones Clase B
            if bvps > 1000.0:
                bvps = bvps / 1500.0
        elif price_to_book_raw is not None and current_price > 5.0:
            ptb = float(price_to_book_raw)
            # Si priceToBook reportado por Yahoo es extremadamente bajo (<0.05) mientras la cotización es >$5,
            # el valor libro está en unidades de Clase A o ADR sin dividir
            if ptb < 0.05 and bvps > current_price * 5.0:
                ratio = bvps / current_price
                if ratio > 500:
                    bvps = bvps / 1500.0
                else:
                    bvps = current_price / 1.5

        # 3. Normalización de Ganancias (Operating vs GAAP mark-to-market swings en financieras)
        effective_eps = eps
        if is_financial and forward_eps > 0 and eps > forward_eps * 1.4:
            # En financieras/conglomerados, las fluctuaciones no realizadas de la cartera distorsionan el GAAP EPS
            effective_eps = forward_eps

        # Dividendos normalizados
        dividend_rate = float(info.get("dividendRate") or 0.0)
        div_yield_raw = info.get("dividendYield")
        if dividend_rate > 0 and current_price > 0:
            dividend_yield_pct = (dividend_rate / current_price) * 100.0
        elif div_yield_raw is not None:
            raw_val = float(div_yield_raw)
            dividend_yield_pct = raw_val * 100.0 if raw_val < 0.25 else raw_val
        else:
            dividend_yield_pct = 0.0

        # Crecimiento normalizado (acotado para evitar proyecciones distorsionadas)
        raw_growth = info.get("earningsGrowth") or info.get("revenueGrowth")
        if raw_growth is not None:
            growth_rate = float(raw_growth)
        else:
            growth_rate = 0.08

        # --- CÁLCULO DE MODELOS DE VALOR INTRÍNSECO ---
        models = []

        # 1. Modelo de Flujo de Caja Descontado (DCF 2-Etapas: 5 años + Valor Terminal)
        if fcf > 0 and effective_shares > 0:
            dcf_model = FundamentalService._calculate_dcf(
                fcf=fcf,
                shares=effective_shares,
                growth_rate=growth_rate,
                beta=beta,
                total_cash=total_cash,
                total_debt=total_debt,
                current_price=current_price,
                is_financial=is_financial
            )
            if dcf_model:
                if is_financial:
                    dcf_model["weight"] = 0.75
                models.append(dcf_model)

        # 2. Modelo de Peter Lynch (GARP - PEG = 1.0)
        if effective_eps > 0:
            lynch_model = FundamentalService._calculate_peter_lynch(
                eps=effective_eps,
                growth_rate=growth_rate,
                dividend_yield_pct=dividend_yield_pct,
                current_price=current_price
            )
            if lynch_model:
                models.append(lynch_model)

        # 3. Número de Benjamin Graham (Classic Value Investing)
        if effective_eps > 0 and bvps > 0:
            graham_model = FundamentalService._calculate_graham_number(
                eps=effective_eps,
                bvps=bvps,
                current_price=current_price
            )
            if graham_model:
                models.append(graham_model)

        # 4. Múltiplo P/E Normalizado sobre Ganancias Futuras (Forward P/E)
        if forward_eps > 0:
            pe_model = FundamentalService._calculate_pe_multiple(
                forward_eps=forward_eps,
                growth_rate=growth_rate,
                current_price=current_price
            )
            if pe_model:
                models.append(pe_model)

        # 5. Múltiplo EV / EBITDA (Valor de Firma Operativo - No aplicable a sector financiero)
        if not is_financial and ebitda > 0 and effective_shares > 0:
            ev_model = FundamentalService._calculate_ev_ebitda(
                ebitda=ebitda,
                total_debt=total_debt,
                total_cash=total_cash,
                shares=effective_shares,
                current_price=current_price
            )
            if ev_model:
                models.append(ev_model)

        # 6. Modelo de Valor Libro Justificado por ROE (Para entidades financieras y aseguradoras)
        if is_financial and bvps > 0:
            roe_val = float(info.get("returnOnEquity") or 0.12)
            pb_model = FundamentalService._calculate_justified_pb(
                bvps=bvps,
                roe=roe_val,
                beta=beta,
                current_price=current_price
            )
            if pb_model:
                models.append(pb_model)

        # 7. Modelo de Gordon Growth (DDM - Dividend Discount Model)
        if dividend_rate > 0 and dividend_yield_pct >= 1.2:
            ddm_model = FundamentalService._calculate_gordon_ddm(
                dividend_rate=dividend_rate,
                growth_rate=growth_rate,
                beta=beta,
                current_price=current_price
            )
            if ddm_model:
                models.append(ddm_model)

        # 8. Consenso de Analistas de Wall Street
        analyst_target = info.get("targetMeanPrice")
        if analyst_target and float(analyst_target) > 0:
            wallst_model = FundamentalService._calculate_wallst_consensus(
                target_mean=float(analyst_target),
                target_high=info.get("targetHighPrice"),
                target_low=info.get("targetLowPrice"),
                recommendation=info.get("recommendationKey"),
                analysts_count=info.get("numberOfAnalystOpinions"),
                current_price=current_price
            )
            if wallst_model:
                models.append(wallst_model)

        # --- SÍNTESIS, PROMEDIO Y VEREDICTO ---
        summary = FundamentalService._synthesize_valuation(models, current_price)

        # Recopilación de Métricas Fundamentales Completas
        metrics = FundamentalService._extract_complete_metrics(info, current_price, dividend_yield_pct)

        result = {
            "ticker": ticker_clean,
            "company_name": info.get("longName") or info.get("shortName") or ticker_clean,
            "is_etf": False,
            "current_price": current_price,
            "summary": summary,
            "models": models,
            "metrics": metrics,
            "profile": {
                "sector": info.get("sector") or "Desconocido",
                "industry": info.get("industry") or "Desconocido",
                "country": info.get("country") or "Desconocido",
                "website": info.get("website") or "",
                "description": info.get("longBusinessSummary") or "Sin descripción disponible."
            }
        }

        _fundamental_cache.set(ticker_clean, result)
        return result

    # --- MÉTODOS DE MODELOS DE VALORACIÓN ---

    @staticmethod
    def _calculate_dcf(fcf: float, shares: float, growth_rate: float, beta: float,
                       total_cash: float, total_debt: float, current_price: float,
                       is_financial: bool = False) -> dict:
        """Modelo DCF 2 etapas: proyección a 5 años con desvanecimiento de crecimiento y valor terminal."""
        fcf_per_share = fcf / shares
        
        # Tasa de descuento WACC derivada de CAPM: Rf 4.2% + Beta * 5.0% ERP
        discount_rate = min(max(0.042 + beta * 0.05, 0.08), 0.12)
        
        # Tasa de crecimiento inicial acotada (conservadora)
        g1 = min(max(growth_rate, 0.04), 0.18)
        terminal_growth = 0.025 # 2.5% crecimiento perpétuo
        
        # Proyección a 5 años
        pv_cf = 0.0
        cf_projected = fcf_per_share
        for yr in range(1, 6):
            cf_projected *= (1.0 + g1 * (0.95 ** (yr - 1)))
            pv_cf += cf_projected / ((1.0 + discount_rate) ** yr)

        # Valor Terminal descontado
        terminal_value = (cf_projected * (1.0 + terminal_growth)) / (discount_rate - terminal_growth)
        pv_terminal = terminal_value / ((1.0 + discount_rate) ** 5)

        # Ajuste de Caja Neta / Deuda por acción:
        # En sector financiero y aseguradoras, el efectivo es float operativo y la deuda son pasivos operativos; no se suma
        net_cash_per_share = 0.0 if is_financial else ((total_cash - total_debt) / shares)
        dcf_fair_value = pv_cf + pv_terminal + net_cash_per_share

        if dcf_fair_value <= 0:
            return None

        diff_pct = round(((dcf_fair_value - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "dcf",
            "name": "Flujo de Caja Descontado (DCF 5a)",
            "value": round(dcf_fair_value, 2),
            "weight": 1.25,
            "diff_pct": diff_pct,
            "description": "Valor presente de los flujos libres de caja futuros más valor terminal neto de deuda." if not is_financial else "Valor presente de flujos libres proyectados (sin distorsión de float o reservas bancarias).",
            "assumptions": {
                "fcf_por_accion": round(fcf_per_share, 2),
                "tasa_descuento_wacc": f"{round(discount_rate * 100, 1)}%",
                "crecimiento_fcf_inicial": f"{round(g1 * 100, 1)}%",
                "crecimiento_terminal": "2.5%",
                "ajuste_caja_deuda_accion": f"${round(net_cash_per_share, 2)}" if not is_financial else "Excluido (Float de Seguros / Depósitos)"
            }
        }

    @staticmethod
    def _calculate_peter_lynch(eps: float, growth_rate: float, dividend_yield_pct: float, current_price: float) -> dict:
        """Valor Peter Lynch: En una valoración justa, el ratio P/E equivale al crecimiento anual (PEG = 1.0)."""
        # Crecimiento acotado entre 6% y 25% para evitar extremos cíclicos
        lynch_growth = min(max(growth_rate * 100.0, 6.0), 25.0)
        div_adj = min(dividend_yield_pct, 6.0)
        fair_pe = lynch_growth + div_adj
        lynch_value = eps * fair_pe

        diff_pct = round(((lynch_value - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "peter_lynch",
            "name": "Valor Justo Peter Lynch (PEG 1.0)",
            "value": round(lynch_value, 2),
            "weight": 1.0,
            "diff_pct": diff_pct,
            "description": "Regla clásica de Peter Lynch: un ratio P/E justo equivale al crecimiento anual más dividendos.",
            "assumptions": {
                "eps_beneficio_por_accion": round(eps, 2),
                "tasa_crecimiento_estimada": f"{round(lynch_growth, 1)}%",
                "ajuste_por_dividendo": f"{round(div_adj, 2)}%",
                "pe_justo_objetivo": round(fair_pe, 1)
            }
        }

    @staticmethod
    def _calculate_graham_number(eps: float, bvps: float, current_price: float) -> dict:
        """Número de Graham: sqrt(22.5 * EPS * BookValue)."""
        graham_val = math.sqrt(22.5 * eps * bvps)
        diff_pct = round(((graham_val - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "graham",
            "name": "Número de Benjamin Graham",
            "value": round(graham_val, 2),
            "weight": 0.85,
            "diff_pct": diff_pct,
            "description": "Fórmula del padre del Value Investing para empresas defensivas con P/E <= 15 y P/B <= 1.5.",
            "assumptions": {
                "eps": round(eps, 2),
                "valor_libro_por_accion": round(bvps, 2),
                "multiplicador_graham": 22.5
            }
        }

    @staticmethod
    def _calculate_pe_multiple(forward_eps: float, growth_rate: float, current_price: float) -> dict:
        """Múltiplo P/E Normalizado sobre beneficios futuros."""
        # P/E benchmark entre 16x y 24x ajustado ligeramente por crecimiento
        target_pe = min(max(16.0 + (growth_rate * 30.0), 16.0), 24.0)
        pe_val = forward_eps * target_pe
        diff_pct = round(((pe_val - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "pe_multiple",
            "name": "Múltiplo P/E Normalizado",
            "value": round(pe_val, 2),
            "weight": 0.9,
            "diff_pct": diff_pct,
            "description": "Valoración basada en ganancias futuras esperadas cotizando a un múltiplo P/E razonable.",
            "assumptions": {
                "eps_forward": round(forward_eps, 2),
                "multiplo_pe_benchmark": round(target_pe, 1)
            }
        }

    @staticmethod
    def _calculate_ev_ebitda(ebitda: float, total_debt: float, total_cash: float,
                             shares: float, current_price: float) -> dict:
        """Valoración de firma por múltiplo EV / EBITDA (13.0x)."""
        target_multiple = 13.0
        implied_ev = ebitda * target_multiple
        implied_equity = implied_ev - total_debt + total_cash
        fair_val = implied_equity / shares

        if fair_val <= 0:
            return None

        diff_pct = round(((fair_val - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "ev_ebitda",
            "name": "Múltiplo EV / EBITDA (13x)",
            "value": round(fair_val, 2),
            "weight": 0.9,
            "diff_pct": diff_pct,
            "description": "Valoración operativa de la empresa respecto a su generación de EBITDA, neta de endeudamiento.",
            "assumptions": {
                "ebitda_anual_billones": f"${round(ebitda / 1e9, 2)}B",
                "multiplo_ev_ebitda": 13.0,
                "deuda_neta_por_accion": f"${round((total_debt - total_cash) / shares, 2)}"
            }
        }

    @staticmethod
    def _calculate_justified_pb(bvps: float, roe: float, beta: float, current_price: float) -> dict:
        """
        Modelo de Valor Libro Justificado por Retorno sobre Patrimonio (Justified P/B por ROE).
        Estándar de la industria financiera para valorar bancos y aseguradoras (Gordon-RoE / Residual Income).
        """
        # Costo del capital propio (Cost of Equity - Ke)
        ke = min(max(0.042 + beta * 0.05, 0.08), 0.12)
        # Crecimiento a largo plazo acotado al crecimiento del PIB
        g = 0.025
        # ROE acotado a niveles razonables de ciclo económico (5% a 25%)
        effective_roe = min(max(roe, 0.05), 0.25)

        # Múltiplo P/B justificado: (ROE - g) / (Ke - g)
        if ke > g:
            justified_pb = (effective_roe - g) / (ke - g)
        else:
            justified_pb = 1.0

        # Acotamos el múltiplo P/B justificado a un rango saludable (0.7x a 2.5x)
        justified_pb = min(max(justified_pb, 0.7), 2.5)

        fair_val = bvps * justified_pb
        diff_pct = round(((fair_val - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "justified_pb",
            "name": "Valor Libro Justificado (P/B ROE)",
            "value": round(fair_val, 2),
            "weight": 1.1,
            "diff_pct": diff_pct,
            "description": "Estándar de valoración para entidades financieras según su retorno sobre patrimonio (ROE vs Coste de Capital).",
            "assumptions": {
                "valor_libro_por_accion": f"${round(bvps, 2)}",
                "roe_efectivo": f"{round(effective_roe * 100, 1)}%",
                "coste_capital_ke": f"{round(ke * 100, 1)}%",
                "multiplo_pb_justificado": f"{round(justified_pb, 2)}x"
            }
        }

    @staticmethod
    def _calculate_gordon_ddm(dividend_rate: float, growth_rate: float, beta: float, current_price: float) -> dict:
        """Modelo Gordon Growth de Descuento de Dividendos (DDM)."""
        cost_of_equity = min(max(0.042 + beta * 0.045, 0.075), 0.10)
        div_growth = min(max(growth_rate * 0.5, 0.02), 0.045)

        if cost_of_equity <= div_growth:
            return None

        d1 = dividend_rate * (1.0 + div_growth)
        ddm_val = d1 / (cost_of_equity - div_growth)

        diff_pct = round(((ddm_val - current_price) / current_price) * 100, 1) if current_price else 0.0

        return {
            "id": "ddm",
            "name": "Modelo Dividendos Gordon (DDM)",
            "value": round(ddm_val, 2),
            "weight": 0.8,
            "diff_pct": diff_pct,
            "description": "Valor actual del flujo perpetuo de dividendos esperados para empresas maduras y pagadoras.",
            "assumptions": {
                "dividendo_anual": f"${round(dividend_rate, 2)}",
                "costo_de_capital": f"{round(cost_of_equity * 100, 1)}%",
                "crecimiento_dividendo": f"{round(div_growth * 100, 1)}%"
            }
        }

    @staticmethod
    def _calculate_wallst_consensus(target_mean: float, target_high, target_low,
                                    recommendation: str, analysts_count, current_price: float) -> dict:
        """Consenso de analistas de inversión de Wall Street."""
        diff_pct = round(((target_mean - current_price) / current_price) * 100, 1) if current_price else 0.0

        rec_spanish = {
            "strong_buy": "Fuerte Compra",
            "buy": "Compra",
            "hold": "Mantener",
            "underperform": "Bajo Rendimiento",
            "sell": "Vender"
        }.get(str(recommendation).lower(), "Neutral")

        return {
            "id": "wallst_consensus",
            "name": "Consenso Analistas de Wall St",
            "value": round(target_mean, 2),
            "weight": 1.1,
            "diff_pct": diff_pct,
            "description": "Precio objetivo promedio calculado por analistas financieros profesionales de Wall Street.",
            "assumptions": {
                "consenso_recomendacion": rec_spanish,
                "analistas_cobertura": analysts_count or "Varios",
                "objetivo_maximo": f"${round(float(target_high), 2)}" if target_high else "-",
                "objetivo_minimo": f"${round(float(target_low), 2)}" if target_low else "-"
            }
        }

    # --- SÍNTESIS Y MÉTRICAS FUNDAMENTALES ---

    @staticmethod
    def _synthesize_valuation(models: list, current_price: float) -> dict:
        """Calcula el promedio ponderado, rango min/max, margen de seguridad y veredicto cuantitativo."""
        if not models:
            return {
                "average_fair_value": 0.0,
                "min_fair_value": 0.0,
                "max_fair_value": 0.0,
                "current_price": current_price,
                "discount_pct": 0.0,
                "margin_of_safety_pct": 0.0,
                "verdict": "no_data",
                "verdict_label": "Datos Insuficientes",
                "verdict_color": "gray",
                "models_count": 0
            }

        # 1. Mediana estadística para detección robusta de outliers
        values = [m["value"] for m in models]
        values_sorted = sorted(values)
        n = len(values_sorted)
        if n % 2 == 1:
            median_val = values_sorted[n // 2]
        else:
            median_val = (values_sorted[n // 2 - 1] + values_sorted[n // 2]) / 2.0

        # 2. Detección y poda de outliers mediante Calibración Dual (Mediana + Corredor de Mercado)
        valid_models = []
        for m in models:
            val = m["value"]
            is_outlier = False
            outlier_reason = None
            model_id = m.get("id")

            # Regla 1: El consenso de analistas de Wall Street es un ancla exógena empírica;
            # nunca se poda salvo que sea <= 0
            if model_id == "wallst_consensus":
                m["is_outlier"] = False
                valid_models.append(m)
                continue

            # Regla 2: Corredor de Realidad de Mercado (Market Reality Corridor)
            # Si el valor intrínseco calculado está entre 35% y 250% del precio de mercado,
            # está económicamente anclado y nunca debe ser descartado como outlier,
            # evitando que medianas distorsionadas por modelos retrospectivos lo eliminen.
            is_within_market_corridor = (
                current_price > 0 and (0.35 * current_price <= val <= 2.5 * current_price)
            )

            if not is_within_market_corridor:
                # Si está fuera del corredor de mercado, evaluamos si es un outlier genuino:
                # A) Outlier Superior: supera 3x la mediana Y supera 2.5x la cotización
                if median_val > 0 and val > median_val * 3.0 and (current_price == 0 or val > current_price * 2.5):
                    is_outlier = True
                    outlier_reason = f"Valor atípico (${round(val, 2)}) muy superior tanto a la mediana (${round(median_val, 2)}) como a la cotización"
                # B) Outlier Superior Extremo sin respaldo: supera 4x el precio de mercado
                elif current_price > 0 and val > current_price * 4.0:
                    is_outlier = True
                    outlier_reason = f"Valor (${round(val, 2)}) supera 4x la cotización de mercado sin respaldo de analistas"
                # C) Outlier Inferior: inferior al 30% de la mediana Y al 30% del precio
                elif median_val > 0 and val < median_val * 0.30 and (current_price == 0 or val < current_price * 0.30):
                    is_outlier = True
                    outlier_reason = f"Valor atípico (${round(val, 2)}) muy inferior tanto a la mediana (${round(median_val, 2)}) como a la cotización"

            m["is_outlier"] = is_outlier
            if is_outlier:
                m["outlier_reason"] = outlier_reason
            else:
                valid_models.append(m)

        # Si todos fueron marcados como outliers (caso extremo), usar todos
        models_for_avg = valid_models if valid_models else models

        total_weight = sum(m["weight"] for m in models_for_avg)
        weighted_avg = sum(m["value"] * m["weight"] for m in models_for_avg) / total_weight if total_weight > 0 else 0.0

        active_vals = [m["value"] for m in models_for_avg]
        min_val = min(active_vals)
        max_val = max(active_vals)

        # Margen de Seguridad / Descuento: (Valor Justo - Precio) / Precio
        discount_pct = round(((weighted_avg - current_price) / current_price) * 100, 1) if current_price else 0.0

        if discount_pct >= 25.0:
            verdict = "deeply_undervalued"
            verdict_label = "Muy Barata (Fuerte Oportunidad)"
            verdict_color = "emerald"
        elif discount_pct >= 8.0:
            verdict = "undervalued"
            verdict_label = "Barata (Infravalorada)"
            verdict_color = "green"
        elif discount_pct >= -8.0:
            verdict = "fair_value"
            verdict_label = "En Precio Justo (Fair Value)"
            verdict_color = "amber"
        elif discount_pct >= -25.0:
            verdict = "overvalued"
            verdict_label = "Cara (Sobrevalorada)"
            verdict_color = "orange"
        else:
            verdict = "deeply_overvalued"
            verdict_label = "Muy Cara (Fuerte Sobreprecio)"
            verdict_color = "red"

        return {
            "average_fair_value": round(weighted_avg, 2),
            "min_fair_value": round(min_val, 2),
            "max_fair_value": round(max_val, 2),
            "current_price": round(current_price, 2),
            "discount_pct": discount_pct,
            "margin_of_safety_pct": discount_pct,
            "verdict": verdict,
            "verdict_label": verdict_label,
            "verdict_color": verdict_color,
            "models_count": len(models),
            "outliers_count": len(models) - len(valid_models)
        }

    @staticmethod
    def _extract_complete_metrics(info: dict, current_price: float, dividend_yield_pct: float) -> dict:
        """Extrae de forma limpia y estructurada todas las métricas fundamentales para la UI."""
        low_52 = float(info.get("fiftyTwoWeekLow") or 0.0)
        high_52 = float(info.get("fiftyTwoWeekHigh") or 0.0)
        range_position_pct = 0.0
        if high_52 > low_52 and current_price >= low_52:
            range_position_pct = round(((current_price - low_52) / (high_52 - low_52)) * 100, 1)
            range_position_pct = min(max(range_position_pct, 0.0), 100.0)

        # Formatear porcentajes de márgenes
        def to_pct(val):
            return round(float(val) * 100, 2) if val is not None else None

        return {
            "valuation": {
                "trailing_pe": round(float(info.get("trailingPE")), 2) if info.get("trailingPE") else None,
                "forward_pe": round(float(info.get("forwardPE")), 2) if info.get("forwardPE") else None,
                "peg_ratio": round(float(info.get("pegRatio")), 2) if info.get("pegRatio") else None,
                "price_to_book": round(float(info.get("priceToBook")), 2) if info.get("priceToBook") else None,
                "price_to_sales": round(float(info.get("priceToSalesTrailing12Months")), 2) if info.get("priceToSalesTrailing12Months") else None,
                "ev_to_ebitda": round(float(info.get("enterpriseToEbitda")), 2) if info.get("enterpriseToEbitda") else None,
                "ev_to_revenue": round(float(info.get("enterpriseToRevenue")), 2) if info.get("enterpriseToRevenue") else None,
            },
            "profitability": {
                "profit_margin_pct": to_pct(info.get("profitMargins")),
                "operating_margin_pct": to_pct(info.get("operatingMargins")),
                "gross_margin_pct": to_pct(info.get("grossMargins")),
                "return_on_equity_pct": to_pct(info.get("returnOnEquity")),
                "return_on_assets_pct": to_pct(info.get("returnOnAssets")),
            },
            "health": {
                "debt_to_equity": round(float(info.get("debtToEquity")), 2) if info.get("debtToEquity") else None,
                "current_ratio": round(float(info.get("currentRatio")), 2) if info.get("currentRatio") else None,
                "quick_ratio": round(float(info.get("quickRatio")), 2) if info.get("quickRatio") else None,
                "total_cash": float(info.get("totalCash")) if info.get("totalCash") else None,
                "total_debt": float(info.get("totalDebt")) if info.get("totalDebt") else None,
                "free_cash_flow": float(info.get("freeCashflow")) if info.get("freeCashflow") else None,
                "operating_cash_flow": float(info.get("operatingCashflow")) if info.get("operatingCashflow") else None,
            },
            "growth_and_dividends": {
                "revenue_growth_yoy_pct": to_pct(info.get("revenueGrowth")),
                "earnings_growth_yoy_pct": to_pct(info.get("earningsGrowth")),
                "dividend_yield_pct": round(dividend_yield_pct, 2) if dividend_yield_pct > 0 else 0.0,
                "dividend_rate": round(float(info.get("dividendRate")), 2) if info.get("dividendRate") else 0.0,
                "payout_ratio_pct": to_pct(info.get("payoutRatio")),
            },
            "market_stats": {
                "market_cap": float(info.get("marketCap")) if info.get("marketCap") else None,
                "enterprise_value": float(info.get("enterpriseValue")) if info.get("enterpriseValue") else None,
                "beta": round(float(info.get("beta")), 2) if info.get("beta") else 1.0,
                "fifty_two_week_low": low_52,
                "fifty_two_week_high": high_52,
                "range_position_pct": range_position_pct,
                "shares_outstanding": float(info.get("sharesOutstanding")) if info.get("sharesOutstanding") else None,
            }
        }

    @staticmethod
    def _build_etf_response(ticker: str, current_price: float, info: dict) -> dict:
        """Genera respuesta especializada para ETFs y Fondos Indexados."""
        low_52 = float(info.get("fiftyTwoWeekLow") or 0.0)
        high_52 = float(info.get("fiftyTwoWeekHigh") or 0.0)
        range_pos = 0.0
        if high_52 > low_52 and current_price >= low_52:
            range_pos = round(((current_price - low_52) / (high_52 - low_52)) * 100, 1)

        raw_yield = info.get("yield") or info.get("dividendYield")
        div_yield_pct = float(raw_yield) * 100.0 if raw_yield and float(raw_yield) < 0.25 else float(raw_yield or 0.0)

        nav_price = float(info.get("navPrice") or 0.0)
        nav_diff_pct = round(((current_price - nav_price) / nav_price) * 100, 2) if nav_price > 0 else 0.0

        return {
            "ticker": ticker,
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "is_etf": True,
            "current_price": current_price,
            "summary": {
                "average_fair_value": nav_price if nav_price > 0 else current_price,
                "min_fair_value": nav_price if nav_price > 0 else current_price,
                "max_fair_value": nav_price if nav_price > 0 else current_price,
                "current_price": current_price,
                "discount_pct": round(-nav_diff_pct, 1),
                "margin_of_safety_pct": round(-nav_diff_pct, 1),
                "verdict": "etf_index",
                "verdict_label": "ETF / Fondo Indexado",
                "verdict_color": "blue",
                "models_count": 0,
                "etf_note": "Los modelos de flujo de caja descontado (DCF) o Graham aplican a corporaciones individuales. Para este ETF se evalúa su valor liquidativo (NAV) y métricas de su cesta de valores."
            },
            "models": [],
            "metrics": {
                "valuation": {
                    "trailing_pe": round(float(info.get("trailingPE")), 2) if info.get("trailingPE") else None,
                    "nav_price": nav_price if nav_price > 0 else None,
                    "nav_premium_discount_pct": nav_diff_pct,
                },
                "profitability": {},
                "health": {
                    "total_assets": float(info.get("totalAssets")) if info.get("totalAssets") else None,
                },
                "growth_and_dividends": {
                    "dividend_yield_pct": round(div_yield_pct, 2),
                },
                "market_stats": {
                    "beta": round(float(info.get("beta")), 2) if info.get("beta") else 1.0,
                    "fifty_two_week_low": low_52,
                    "fifty_two_week_high": high_52,
                    "range_position_pct": range_pos,
                }
            },
            "profile": {
                "sector": "Fondo Indexado / ETF",
                "industry": info.get("category") or "Diversificado",
                "country": "Global",
                "website": "",
                "description": info.get("longBusinessSummary") or f"ETF {ticker} que replica un índice o canasta de activos diversificados."
            }
        }
