import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  ClockCounterClockwise, Trash, Eye, Export,
  Devices, VideoCamera, ShieldWarning, Calendar,
} from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

const API = `${process.env.REACT_APP_BACKEND_URL || "http://localhost:8000"}/api`;

function formatDate(iso) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export default function ScanHistory() {
  const [scans, setScans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedScan, setExpandedScan] = useState(null);

  const fetchScans = useCallback(async () => {
    try {
      const response = await fetch(`${API}/scans`);
      if (!response.ok) {
        throw new Error(`Scans request failed with ${response.status}`);
      }
      const data = await response.json();
      setScans(data);
    } catch (err) {
      toast.error("Failed to load scan history");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchScans(); }, [fetchScans]);

  const deleteScan = async () => {
    if (!deleteId) return;
    try {
      const response = await fetch(`${API}/scans/${deleteId}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        throw new Error(`Delete request failed with ${response.status}`);
      }
      setScans((prev) => prev.filter((s) => s.id !== deleteId));
      toast.success("Scan deleted");
    } catch {
      toast.error("Delete failed");
    }
    setDeleteId(null);
  };

  const viewScan = async (id) => {
    if (expandedId === id) {
      setExpandedId(null);
      setExpandedScan(null);
      return;
    }
    try {
      const response = await fetch(`${API}/scans/${id}`);
      if (!response.ok) {
        throw new Error(`Scan detail request failed with ${response.status}`);
      }
      const data = await response.json();
      setExpandedScan(data);
      setExpandedId(id);
    } catch {
      toast.error("Failed to load scan details");
    }
  };

  const exportScan = async (id) => {
    try {
      const response = await fetch(`${API}/scans/${id}/export`);
      if (!response.ok) {
        throw new Error(`Export request failed with ${response.status}`);
      }
      const data = await response.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `scan-${id.slice(0, 8)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Exported");
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <div data-testid="scan-history-page" className="min-h-screen p-4 md:p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-heading font-black text-2xl sm:text-3xl tracking-tight text-white">
            Scan History
          </h1>
          <p className="text-sm text-[#8A8A8E] mt-1">
            {scans.length} scan{scans.length !== 1 ? "s" : ""} recorded
          </p>
        </div>
      </div>

      {/* Scan List */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-scan/30 border-t-scan rounded-full animate-spin" />
        </div>
      ) : scans.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 border border-white/10 bg-surface rounded-lg">
          <ClockCounterClockwise size={48} weight="duotone" className="text-[#636366] mb-4" />
          <h3 className="font-heading font-bold text-lg text-white mb-2">No Scans Yet</h3>
          <p className="text-sm text-[#8A8A8E]">Go to Scanner to run your first scan.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {scans.map((scan, i) => (
            <motion.div
              key={scan.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.05 }}
            >
              <div
                data-testid={`scan-item-${i}`}
                className="border border-white/10 bg-surface rounded-lg overflow-hidden"
              >
                {/* Scan Header Row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 gap-3">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-md bg-scan/10 flex items-center justify-center flex-shrink-0">
                      <Devices size={20} weight="duotone" className="text-scan" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-white">{scan.subnet}</span>
                        <Badge className="rounded-sm text-[10px] px-1.5 py-0 font-mono bg-scan/20 border border-scan/30 text-scan">
                          {scan.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-[#636366]">
                        <span className="flex items-center gap-1 font-mono">
                          <Calendar size={12} />
                          {formatDate(scan.started_at)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Devices size={12} />
                          {scan.total_devices} devices
                        </span>
                        {scan.cameras_found > 0 && (
                          <span className="flex items-center gap-1 text-danger">
                            <VideoCamera size={12} weight="fill" />
                            {scan.cameras_found} camera{scan.cameras_found > 1 ? "s" : ""}
                          </span>
                        )}
                        {scan.high_risk_count > 0 && (
                          <span className="flex items-center gap-1 text-warning">
                            <ShieldWarning size={12} weight="fill" />
                            {scan.high_risk_count} high risk
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      data-testid={`view-scan-${i}`}
                      onClick={() => viewScan(scan.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-[#8A8A8E] hover:text-white hover:bg-white/5 border border-white/10 rounded-md transition-colors"
                    >
                      <Eye size={14} />
                      {expandedId === scan.id ? "Hide" : "View"}
                    </button>
                    <button
                      data-testid={`export-scan-${i}`}
                      onClick={() => exportScan(scan.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-[#8A8A8E] hover:text-white hover:bg-white/5 border border-white/10 rounded-md transition-colors"
                    >
                      <Export size={14} />
                    </button>
                    <button
                      data-testid={`delete-scan-${i}`}
                      onClick={() => setDeleteId(scan.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono text-danger/70 hover:text-danger hover:bg-danger/5 border border-white/10 rounded-md transition-colors"
                    >
                      <Trash size={14} />
                    </button>
                  </div>
                </div>

                {/* Expanded Device List */}
                {expandedId === scan.id && expandedScan && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    className="border-t border-white/10"
                  >
                    <div className="p-4 max-h-64 overflow-y-auto">
                      <div className="space-y-1">
                        {expandedScan.devices.map((d, j) => (
                          <div
                            key={d.id}
                            className="flex items-center justify-between py-2 px-3 rounded-md hover:bg-white/[0.03] transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-xs text-white w-28">{d.ip}</span>
                              <span className="font-mono text-[11px] text-[#636366] w-36 hidden md:block">{d.mac}</span>
                              <span className="text-xs text-[#8A8A8E] w-24 hidden lg:block">{d.vendor}</span>
                            </div>
                            <div className="flex items-center gap-3">
                              <Badge className={`rounded-sm text-[10px] px-1.5 py-0 font-mono ${
                                d.device_type.includes("Camera")
                                  ? "bg-danger/20 border border-danger/50 text-danger"
                                  : "bg-white/5 border border-white/10 text-[#8A8A8E]"
                              }`}>
                                {d.device_type}
                              </Badge>
                              <span className={`font-mono text-xs font-bold ${
                                d.risk_score >= 70 ? "text-danger" :
                                d.risk_score >= 40 ? "text-[#FF9500]" :
                                d.risk_score >= 20 ? "text-warning" : "text-safe"
                              }`}>
                                {d.risk_score}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent className="bg-surface border border-white/10 text-white sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-heading text-white">Delete Scan</DialogTitle>
            <DialogDescription className="text-[#8A8A8E]">
              This action cannot be undone. The scan and all associated data will be permanently removed.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <button
              data-testid="cancel-delete-btn"
              onClick={() => setDeleteId(null)}
              className="px-4 py-2 text-sm border border-white/20 text-white rounded-md hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              data-testid="confirm-delete-btn"
              onClick={deleteScan}
              className="px-4 py-2 text-sm bg-danger text-white rounded-md font-bold hover:bg-[#CC2F26] transition-colors"
            >
              Delete
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
