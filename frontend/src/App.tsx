import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardHome from './components/DashboardHome';
import MarketView from './pages/MarketView';
import CashFlow from './pages/CashFlow';
import AnalyticsView from './pages/AnalyticsView';
import OracleView from './pages/OracleView';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/cash" element={<CashFlow />} />
          <Route path="/market" element={<MarketView />} />
          <Route path="/analytics" element={<AnalyticsView />} />
          <Route path="/oracle" element={<OracleView />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;