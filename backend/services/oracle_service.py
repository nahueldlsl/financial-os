import math

class OracleService:
    @staticmethod
    def generate_insights(risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float):
        """
        Ingiere las métricas cuantivativas del portafolio y genera 
        una bitácora de consejos automatizados de inversión.
        """
        insights = []

        # 1. Regla de Liquidez (Cash Drag)
        cash_ratio = (cash_balance / net_worth) if net_worth > 0 else 0
        if cash_ratio > 0.40:
            insights.append({
                "type": "warning",
                "title": "Exceso de Liquidez Detectado (Cash Drag)",
                "message": f"El {math.floor(cash_ratio * 100)}% de tu portafolio está en efectivo (Broker/Waller). Estás perdiendo poder adquisitivo contra la inflación real.",
                "action_suggested": "Comienza a promediar compras (DCA) en ETFs de base amplia o adquiere Bonos de Corto Plazo (ej: SGOV)."
            })
        elif cash_ratio < 0.05 and net_worth > 1000:
            insights.append({
                "type": "info",
                "title": "Baja Liquidez Operativa",
                "message": "Tienes muy poco efectivo disponible. Ante una caída de mercado (corrección) no tendrás capital para comprar a descuento.",
                "action_suggested": "Asegúrate de tener al menos un 10-15% en caja permanente o en activos altamente líquidos equivalente al dinero fiat."
            })

        # 2. Regla de Recompensa (Sharpe Ratio)
        sf = risk_metrics.get("sharpe_ratio", 0)
        if sf != 0:
            if sf < 0.8:
                insights.append({
                    "type": "danger",
                    "title": "Rendimiento Subóptimo Sistemático",
                    "message": f"Tu Ratio de Sharpe de {sf} indica pobre compensación. El riesgo que asumes no está justificando las ganancias respecto a una Tasa Libre de Riesgo del 4%.",
                    "action_suggested": "Reduce posiciones de alto riesgo/poco dividendo y re-asigna temporalmente a un ETF tipo SPY o QQQ."
                })
            elif sf > 1.5:
                insights.append({
                    "type": "success",
                    "title": "Rendimiento Excepcional (Sharpe > 1.5)",
                    "message": f"Estás logrando un ratio de retornos asimétricos excelente ({sf}). Tu rentabilidad justificada al riesgo supera a los gestores promedio.",
                    "action_suggested": "Mantén la estrategia sin sobre-operar (Overtrading). Reevalúa semestralmente."
                })

        # 3. Regla de Volatilidad Relativa (Beta)
        beta = risk_metrics.get("beta", 1)
        if beta > 1.3:
            insights.append({
                "type": "warning",
                "title": "Portafolio Hiper Reactivo (High Beta)",
                "message": f"Una Beta de {beta} indica que tu portafolio es {(beta - 1) * 100}% más volátil que el S&P 500. Tufrirás un fuerte sangrado si hay 'bear market'.",
                "action_suggested": "Diversifica en sectores defensivos: Utilities, Oro (GLD), o consumo no discrecional."
            })

        # 4. Regla de Drawdown (Caída máxima)
        dd = risk_metrics.get("max_drawdown_pct", 0)
        if dd < -25:
             insights.append({
                "type": "danger",
                "title": "Vulnerabilidad a Grandes Correcciones",
                "message": f"Históricamente este listado de activos cayó un {dd}%. Recuperarte de esa caída requeriría más de un {math.floor(abs(dd)*1.5)}% de beneficio limpio.",
                "action_suggested": "Incorpora activos inelásticos/descorrelacionados o ajusta tu stop-loss global."
            })

        # 5. Reglas de Valuation Concentración
        for asset in valuation_data:
            weight = asset.get("weight_percentage", 0)
            if weight > 30:
                insights.append({
                    "type": "warning",
                    "title": f"Riesgo de Concentración en {asset.get('ticker')}",
                    "message": f"El activo domina un {weight}% del valor invertido. Te enfrentas a un 'Idiosyncratic Risk' que podría hundir el portafolio entero si {asset.get('ticker')} hace 'Miss Earnings'.",
                    "action_suggested": f"Considera hacer 'Take Partials' de {asset.get('ticker')} y redistribuir hacia posiciones estancadas menores al 5%."
                })
                
        # 6. Sin insights
        if not insights:
            insights.append({
                "type": "success",
                "title": "Cartea Equilibrada Mágicamente",
                "message": "Nuestros algoritmos no encuentran métricas perjudiciales a corto plazo. Estás operando en parámetros estadísticamente sanos.",
                "action_suggested": "Relájate."
            })

        return insights
