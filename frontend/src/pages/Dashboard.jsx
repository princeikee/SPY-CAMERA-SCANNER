import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import {
  Crosshair, Devices, VideoCamera, ShieldWarning,
  ShieldCheck, Play, ArrowsClockwise, Export, Funnel,
} from "@phosphor-icons/react";
import MetricCard from "@/components/MetricCard";
import DeviceTable from "@/components/DeviceTable";
import DeviceSheet from "@/components/DeviceSheet";
import ScanAnimation from "@/components/ScanAnimation";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuTrigger, DropdownMenuSeparator, DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";

const API = `${process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"}/api`;

export default function Dashboard() {
  const [scanning, setScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [currentScan, setCurrentScan] = useState(null);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [subnet, setSubnet] = useState("192.168.1.0/24");

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API}/stats`, { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`Stats request failed with ${response.status}`);
      }
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    if (!scanning || !currentScan?.id) return undefined;

    const pollScan = async () => {
      try {
        const response = await fetch(`${API}/scans/${currentScan.id}?t=${Date.now()}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`Scan poll failed with ${response.status}`);
        }
        const data = await response.json();
        setCurrentScan(data);
        setScanProgress(data.progress || 0);

        if (data.status === "completed") {
          setScanning(false);
          fetchStats();
          const cams = data.cameras_found;
          if (cams > 0) {
            toast.error(`${cams} potential camera${cams > 1 ? "s" : ""} detected!`, {
              description: "Review flagged devices for suspicious activity.",
            });
          } else {
            toast.success("Scan complete - no cameras detected", {
              description: `${data.total_devices} devices found on network.`,
            });
          }
        }

        if (data.status === "failed") {
          setScanning(false);
          toast.error("Scan failed", {
            description: data.logs?.[data.logs.length - 1] || "The backend scan job failed.",
          });
        }
      } catch (err) {
        setScanning(false);
        toast.error("Scan failed", { description: err.message });
      }
    };

    pollScan();
    const interval = setInterval(pollScan, 1000);
    return () => clearInterval(interval);
  }, [currentScan?.id, fetchStats, scanning]);

  const startScan = async () => {
    setScanning(true);
    setScanProgress(0);
    setCurrentScan(null);

    try {
      const response = await fetch(`${API}/scans/start`, {
        method: "POST",
        cache: "no-store",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          subnet,
          interface: "eth0",
        }),
      });
      if (!response.ok) {
        throw new Error(`Scan request failed with ${response.status}`);
      }
      const data = await response.json();
      setCurrentScan(data);
      setScanProgress(data.progress || 0);
    } catch (err) {
      setScanning(false);
      toast.error("Scan failed", { description: err.message });
    }
  };

  const exportScan = async () => {
    if (!currentScan) return;
    try {
      const response = await fetch(`${API}/scans/${currentScan.id}/export`);
      if (!response.ok) {
        throw new Error(`Export request failed with ${response.status}`);
      }
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scan-${currentScan.id.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Scan exported");
    } catch {
      toast.error("Export failed");
    }
  };

  const filteredDevices = currentScan?.devices?.filter((d) => {
    if (filter === "cameras") return d.device_type.includes("Camera");
    if (filter === "high-risk") return d.risk_score >= 60;
    if (filter === "safe") return d.risk_score < 20;
    return true;
  }) || [];

  const scanMetrics = currentScan
    ? {
        total: currentScan.total_devices,
        cameras: currentScan.cameras_found,
        highRisk: currentScan.high_risk_count,
        safe: currentScan.total_devices - currentScan.cameras_found,
      }
    : stats
    ? {
        total: stats.total_devices_found,
        cameras: stats.total_cameras_found,
        highRisk: stats.total_high_risk,
        safe: stats.total_devices_found - stats.total_cameras_found,
      }
    : { total: 0, cameras: 0, highRisk: 0, safe: 0 };

  return (
    <div data-testid="dashboard" className="min-h-screen p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="font-heading font-black text-2xl sm:text-3xl tracking-tight text-white">
            Network Scanner
          </h1>
          <p className="text-sm text-[#8A8A8E] mt-1 font-body">
            Detect hidden cameras & surveillance devices on your network
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Subnet input */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-2 bg-app border border-white/10 rounded-md">
            <span className="text-xs font-mono text-[#636366]">SUBNET</span>
            <input
              data-testid="subnet-input"
              type="text"
              value={subnet}
              onChange={(e) => setSubnet(e.target.value)}
              className="bg-transparent text-white font-mono text-sm w-36 focus:outline-none"
            />
          </div>

          {currentScan && (
            <button
              data-testid="export-btn"
              onClick={exportScan}
              className="flex items-center gap-2 px-4 py-2 bg-transparent border border-white/20 text-white hover:bg-white/5 transition-colors rounded-md text-sm font-medium"
            >
              <Export size={16} weight="duotone" />
              <span className="hidden sm:inline">Export</span>
            </button>
          )}

          <button
            data-testid="start-scan-btn"
            onClick={startScan}
            disabled={scanning}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-md text-sm font-bold transition-all ${
              scanning
                ? "bg-scan/20 text-scan cursor-wait animate-glow-pulse"
                : "bg-scan text-white hover:bg-[#0056B3]"
            }`}
          >
            {scanning ? (
              <>
                <ArrowsClockwise size={18} weight="bold" className="animate-spin" />
                Scanning...
              </>
            ) : (
              <>
                <Play size={18} weight="fill" />
                Start Scan
              </>
            )}
          </button>
        </div>
      </div>

      {/* Scan Animation (during scan) */}
      <AnimatePresence>
        {scanning && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="flex flex-col items-center justify-center py-16 mb-8 border border-white/10 bg-surface rounded-lg"
          >
            <ScanAnimation progress={scanProgress} />
            <p className="text-sm text-[#8A8A8E] mt-12 font-mono">
              Scanning network {subnet}...
            </p>
            <p className="text-xs text-[#636366] mt-1 font-mono">
              {currentScan?.scan_engine === "nmap"
                ? "Running nmap service detection..."
                : "Probing ports and collecting live fingerprints..."}
            </p>
            <div className="w-full max-w-2xl mt-8 border border-white/10 bg-app/80 rounded-lg overflow-hidden">
              <div className="px-4 py-2 border-b border-white/10 text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E]">
                Live Scan Logs
              </div>
              <div className="max-h-56 overflow-y-auto px-4 py-3 space-y-2 text-left">
                {(currentScan?.logs?.length ? currentScan.logs : ["Waiting for first backend event..."]).map((line, index) => (
                  <div key={`${line}-${index}`} className="text-xs font-mono text-[#C7C7CC] break-words">
                    {line}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Metrics Grid */}
      {!scanning && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <MetricCard
            icon={Devices}
            label="Devices Found"
            value={scanMetrics.total}
            color="scan"
            delay={0}
            testId="metric-devices"
          />
          <MetricCard
            icon={VideoCamera}
            label="Cameras Detected"
            value={scanMetrics.cameras}
            color="danger"
            delay={0.1}
            testId="metric-cameras"
          />
          <MetricCard
            icon={ShieldWarning}
            label="High Risk"
            value={scanMetrics.highRisk}
            color="warning"
            delay={0.2}
            testId="metric-high-risk"
          />
          <MetricCard
            icon={ShieldCheck}
            label="Safe Devices"
            value={scanMetrics.safe}
            color="safe"
            delay={0.3}
            testId="metric-safe"
          />
        </div>
      )}

      {/* Device List */}
      {!scanning && currentScan && (
        <div>
          {/* Table Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading font-bold text-lg text-white">
              Discovered Devices
            </h2>
            <div className="flex items-center gap-2">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    data-testid="filter-dropdown"
                    className="flex items-center gap-2 px-3 py-2 text-xs font-mono uppercase tracking-wider bg-transparent border border-white/10 text-[#8A8A8E] rounded-md hover:border-white/20 hover:text-white transition-colors"
                  >
                    <Funnel size={14} weight="duotone" />
                    {filter === "all" ? "All Devices" :
                     filter === "cameras" ? "Cameras Only" :
                     filter === "high-risk" ? "High Risk" : "Safe Only"}
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="bg-surface border border-white/10 text-white">
                  <DropdownMenuLabel className="text-xs font-mono text-[#636366] uppercase tracking-wider">
                    Filter Devices
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator className="bg-white/10" />
                  {[
                    { value: "all", label: "All Devices" },
                    { value: "cameras", label: "Cameras Only" },
                    { value: "high-risk", label: "High Risk" },
                    { value: "safe", label: "Safe Only" },
                  ].map((f) => (
                    <DropdownMenuItem
                      key={f.value}
                      data-testid={`filter-${f.value}`}
                      onClick={() => setFilter(f.value)}
                      className={`text-sm cursor-pointer ${
                        filter === f.value ? "text-scan" : "text-[#8A8A8E]"
                      } hover:text-white hover:bg-white/5`}
                    >
                      {f.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <DeviceTable
            devices={filteredDevices}
            onDeviceClick={(d) => {
              setSelectedDevice(d);
              setSheetOpen(true);
            }}
          />

          <div className="mt-3 text-xs font-mono text-[#636366] text-right">
            Showing {filteredDevices.length} of {currentScan.total_devices} devices
          </div>
        </div>
      )}

      {/* Empty State */}
      {!scanning && !currentScan && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex flex-col items-center justify-center py-20 border border-white/10 bg-surface rounded-lg"
        >
          <img
            src="https://static.prod-images.emergentagent.com/jobs/c7245c82-ccf9-4bf2-bf49-04a3b6415698/images/643b1bc210ba1956c7b2c9a131875eeeb22cea576158a57a7f228a0149b35908.png"
            alt="Scanner"
            className="w-32 h-32 opacity-60 mb-6"
          />
          <h3 className="font-heading font-bold text-xl text-white mb-2">
            Ready to Scan
          </h3>
          <p className="text-sm text-[#8A8A8E] mb-6 text-center max-w-sm">
            Click "Start Scan" to discover all devices on your network and detect potential hidden cameras.
          </p>
          <button
            data-testid="empty-state-scan-btn"
            onClick={startScan}
            className="flex items-center gap-2 px-6 py-2.5 bg-scan text-white rounded-md text-sm font-bold hover:bg-[#0056B3] transition-colors"
          >
            <Crosshair size={18} weight="duotone" />
            Begin Network Scan
          </button>
        </motion.div>
      )}

      {/* Device Sheet */}
      <DeviceSheet
        device={selectedDevice}
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
      />
    </div>
  );
}
