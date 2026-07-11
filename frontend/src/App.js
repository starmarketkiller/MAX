import "@/App.css";
import { lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import LiveChartPage from "@/pages/LiveChartPage";

// The immersive 3D landing pulls in three.js — lazy-load so it never ships to
// authenticated users who go straight to the dashboard.
const Landing3D = lazy(() => import("@/pages/Landing3D"));

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center text-muted-foreground">
      Loading…
    </div>
  );
}

function Protected({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <Loading />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

// Front door: logged-in users get the dashboard, everyone else meets the 3D landing.
function Root() {
  const { user, checking } = useAuth();
  if (checking) return <Loading />;
  return user ? <Dashboard section="home" /> : <Navigate to="/landing" replace />;
}

export default function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter basename="/app">
          <AuthProvider>
            <Suspense fallback={<Loading />}>
              <Routes>
                <Route path="/landing" element={<Landing3D />} />
                <Route path="/login" element={<Login />} />
                <Route path="/" element={<Root />} />
                <Route path="/strategies" element={<Protected><Dashboard section="strategies" /></Protected>} />
                <Route path="/optimizer" element={<Protected><Dashboard section="optimizer" /></Protected>} />
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
            </Suspense>
            <Toaster richColors position="top-right" />
          </AuthProvider>
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}
