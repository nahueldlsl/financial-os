import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardHome from './components/DashboardHome';
import MarketView from './pages/MarketView'; // <--- Importamos la nueva página
import CashFlow from './pages/CashFlow';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Ruta Principal: El Dashboard */}
        <Route path="/" element={<DashboardHome />} />
        <Route path="/cash" element={<CashFlow />} />
        {/* Ruta Secundaria: Tu Tabla de Inversiones */}
        <Route path="/market" element={<MarketView />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;