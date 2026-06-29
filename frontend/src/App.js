import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import LiveChartPage from "@/pages/LiveChartPage";

function Protected({ children }) {
  const { user, checking } = useAuth();
  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter basename="/app">
          <AuthProvider>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<Protected><Dashboard section="home" /></Protected>} />
              <Route path="/strategies" element={<Protected><Dashboard section="strategies" /></Protected>} />
              <Route path="/analytics" element={<Protected><Dashboard section="analytics" /></Protected>} />
              <Route path="/whatif" element={<Protected><Dashboard section="whatif" /></Protected>} />
              <Route path="/risk" element={<Protected><Dashboard section="risk" /></Protected>} />
              <Route path="/settings" element={<Protected><Dashboard section="settings" /></Protected>} />
              <Route path="/licenses" element={<Protected><Dashboard section="licenses" /></Protected>} />
              <Route path="/coach" element={<Protected><Dashboard section="coach" /></Protected>} />
              <Route path="/journal" element={<Protected><Dashboard section="journal" /></Protected>} />
              <Route path="/risk-calc" element={<Protected><Dashboard section="risk-calc" /></Protected>} />
              <Route path="/backtest" element={<Protected><Dashboard section="backtest" /></Protected>} />
              <Route path="/calendar" element={<Protected><Dashboard section="calendar" /></Protected>} />
              <Route path="/strategy-analytics" element={<Protected><Dashboard section="strategy-analytics" /></Protected>} />
              <Route path="/chain" element={<Protected><Dashboard section="chain" /></Protected>} />
              <Route path="/local-bridge" element={<Protected><Dashboard section="local-bridge" /></Protected>} />
              <Route path="/chart" element={<Protected><LiveChartPage /></Protected>} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
            <Toaster richColors position="top-right" />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}
