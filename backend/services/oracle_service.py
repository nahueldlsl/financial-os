from abc import ABC, abstractmethod
from typing import List, Dict, Any
import math

class OracleRule(ABC):
    """Interfaz abstracta para reglas de análisis del Oráculo (Open/Closed Principle)"""
    @abstractmethod
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        pass

class LiquidityRule(OracleRule):
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        insights = []
        cash_ratio = (cash_balance / net_worth) if net_worth > 0 else 0
        if cash_ratio > 0.40:
            insights.append({
                "type": "warning",
                "title": "Exceso de Liquidez Detectado (Cash Drag)",
                "message": f"El {math.floor(cash_ratio * 100)}% de tu portafolio está en efectivo (Broker/Wallet). Estás perdiendo poder adquisitivo contra la inflación real.",
                "action_suggested": "Comienza a promediar compras (DCA) en ETFs de base amplia o adquiere Bonos de Corto Plazo (ej: SGOV)."
            })
        elif cash_ratio < 0.05 and net_worth > 1000:
            insights.append({
                "type": "info",
                "title": "Baja Liquidez Operativa",
                "message": "Tienes muy poco efectivo disponible. Ante una caída de mercado (corrección) no tendrás capital para comprar a descuento.",
                "action_suggested": "Asegúrate de tener al menos un 10-15% en caja permanente o en activos altamente líquidos equivalente al dinero fiat."
            })
        return insights

class SharpeRule(OracleRule):
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        insights = []
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
        return insights

class VolatilityBetaRule(OracleRule):
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        insights = []
        beta = risk_metrics.get("beta", 1)
        if beta and beta > 1.3:
            diff_pct = (beta - 1) * 100
            insights.append({
                "type": "warning",
                "title": "Portafolio Hiper Reactivo (High Beta)",
                "message": f"Una Beta de {beta} indica que tu portafolio es {diff_pct:.0f}% más volátil que el S&P 500. Sufrirás un fuerte sangrado si hay 'bear market'.",
                "action_suggested": "Diversifica en sectores defensivos: Utilities, Oro (GLD), o consumo no discrecional."
            })
        return insights

class DrawdownRule(OracleRule):
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        insights = []
        dd = risk_metrics.get("max_drawdown_pct", 0)
        if dd and dd < -25:
            recovery_target = math.floor(abs(dd) * 1.5)
            insights.append({
                "type": "danger",
                "title": "Vulnerabilidad a Grandes Correcciones",
                "message": f"Históricamente este listado de activos cayó un {dd}%. Recuperarte de esa caída requeriría más de un {recovery_target}% de beneficio limpio.",
                "action_suggested": "Incorpora activos inelásticos/descorrelacionados o ajusta tu stop-loss global."
            })
        return insights

class ConcentrationRule(OracleRule):
    def evaluate(self, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        insights = []
        for asset in valuation_data:
            weight = asset.get("weight_percentage", 0)
            if weight > 30:
                ticker = asset.get("ticker", "Activo")
                insights.append({
                    "type": "warning",
                    "title": f"Riesgo de Concentración en {ticker}",
                    "message": f"El activo domina un {weight}% del valor invertido. Te enfrentas a un 'Idiosyncratic Risk' que podría hundir el portafolio entero si {ticker} hace 'Miss Earnings'.",
                    "action_suggested": f"Considera hacer 'Take Partials' de {ticker} y redistribuir hacia posiciones estancadas menores al 5%."
                })
        return insights

class OracleService:
    _rules: List[OracleRule] = [
        LiquidityRule(),
        SharpeRule(),
        VolatilityBetaRule(),
        DrawdownRule(),
        ConcentrationRule()
    ]

    @classmethod
    def register_rule(cls, rule: OracleRule):
        """Permite extender el sistema con nuevas reglas heurísticas (Open/Closed Principle)"""
        cls._rules.append(rule)

    @classmethod
    def generate_insights(cls, risk_metrics: dict, valuation_data: list, net_worth: float, cash_balance: float) -> List[Dict[str, Any]]:
        """
        Ingiere las métricas cuantitativas del portafolio y evalúa las reglas registradas.
        """
        insights = []
        for rule in cls._rules:
            insights.extend(rule.evaluate(risk_metrics, valuation_data, net_worth, cash_balance))

        if not insights:
            insights.append({
                "type": "success",
                "title": "Cartera Equilibrada Mágicamente",
                "message": "Nuestros algoritmos no encuentran métricas perjudiciales a corto plazo. Estás operando en parámetros estadísticamente sanos.",
                "action_suggested": "Relájate."
            })

        return insights
