import pandas as pd
import yfinance as yf
from services.risk_service import RiskMetricsService

class BenchmarkService:
    @staticmethod
    def generate_comparative_chart_data(portfolio_history: pd.Series, benchmark_ticker="^GSPC", period="1mo"):
        """
        Normaliza el rendimiento del portafolio y del mercado a Base 100
        para ser renderizado fácilmente por componentes React (Recharts / Chart.js).
        """
        if portfolio_history.empty:
            return []

        # 1. Descargamos Precios Crudos del S&P 500
        try:
            benchmark_data_raw = yf.download(benchmark_ticker, period=period, progress=False)["Close"]
            if isinstance(benchmark_data_raw, pd.DataFrame):
                benchmark_data_raw = benchmark_data_raw.iloc[:, 0] # Tomar la primera columna si retorna un DF
        except Exception:
            # Fallback a una serie plana plana
            benchmark_data_raw = pd.Series(index=portfolio_history.index, data=[100]*len(portfolio_history))
        
        # 2. Sincronización Estricta de Fechas (Time-Series Alignment)
        # Hacemos join. Al usar ffill rellenamos los días donde el S&P no operó pero nuestra cartera sí (o viceversa)
        df = pd.DataFrame({
            "Portfolio": portfolio_history,
            "Benchmark": benchmark_data_raw
        }).ffill().bfill() # ffill para feriados, bfill por si el día 1 falta
        
        # 3. Filtrado Dinámico y Manejo de Fechas (Aseguramos no tener NAs residuales)
        df = df.dropna()

        if df.empty:
            return []

        # 4. Normalización Base 100 ESTRICTA sobre el PRIMER DÍA del rango filtrado
        first_row = df.iloc[0]
        
        if first_row["Portfolio"] == 0 or first_row["Benchmark"] == 0:
            return []

        # (Valor_Dia_Actual / Valor_Dia_Cero) * 100
        df_base100 = (df / first_row) * 100
        
        # Transformar en lista de diccionarios para el backend
        chart_data = []
        for index, row in df_base100.iterrows():
            # index suele ser Timestamp
            date_str = index.strftime("%Y-%m-%d") if hasattr(index, "strftime") else str(index)
            chart_data.append({
                "date": date_str,
                "portfolio_value": round(float(row["Portfolio"]), 2),
                "benchmark_value": round(float(row["Benchmark"]), 2),
            })
            
        return chart_data
