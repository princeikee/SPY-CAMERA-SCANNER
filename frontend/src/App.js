import "@/index.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Dashboard from "@/pages/Dashboard";
import ScanHistory from "@/pages/ScanHistory";
import Sidebar from "@/components/Sidebar";

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-app">
        <div className="noise-overlay" />
        <Sidebar />
        <main className="flex-1 ml-16 lg:ml-56">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/history" element={<ScanHistory />} />
          </Routes>
        </main>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#121212',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#fff',
              fontFamily: "'IBM Plex Sans', sans-serif",
            },
          }}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
