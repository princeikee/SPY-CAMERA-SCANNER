import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import { motion } from "framer-motion";
import {
  ClockCounterClockwise, Trash, Eye, Export,
  Devices, VideoCamera, ShieldWarning, Calendar,
} from "@phosphor-icons/react";
import { Badge } from "@/components/ui/badge";
import { API_URL } from "@/lib/api";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

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
      const response = await fetch(`${API_URL}/scans`);
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
      const response = await fetch(`${API_URL}/scans/${deleteId}`, {
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
      const response = await fetch(`${API_URL}/scans/${id}`);
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
      const response = await fetch(`${API_URL}/scans/${id}/export`);
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
    <div data-testid="scan-history-page" className="min-h-screen w-full max-w-7xl mx-auto p-4 md:p-6 lg:p-8">
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
                <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div className="flex min-w-0 items-start gap-3 sm:items-center sm:gap-4">
                    <div className="w-10 h-10 rounded-md bg-scan/10 flex items-center justify-center flex-shrink-0">
                      <Devices size={20} weight="duotone" className="text-scan" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="break-all font-mono text-sm text-white">{scan.subnet}</span>
                        <Badge className="rounded-sm text-[10px] px-1.5 py-0 font-mono bg-scan/20 border border-scan/30 text-scan">
                          {scan.status}
                        </Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[#636366]">
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
                  <div className="grid grid-cols-3 gap-2 sm:flex sm:items-center">
                    <button
                      data-testid={`view-scan-${i}`}
                      onClick={() => viewScan(scan.id)}
                      className="flex min-h-11 items-center justify-center gap-1.5 rounded-md border border-white/10 px-3 py-2 text-xs font-mono text-[#8A8A8E] transition-colors hover:bg-white/5 hover:text-white"
                    >
                      <Eye size={14} />
                      {expandedId === scan.id ? "Hide" : "View"}
                    </button>
                    <button
                      data-testid={`export-scan-${i}`}
                      onClick={() => exportScan(scan.id)}
                      className="flex min-h-11 items-center justify-center gap-1.5 rounded-md border border-white/10 px-3 py-2 text-xs font-mono text-[#8A8A8E] transition-colors hover:bg-white/5 hover:text-white"
                      aria-label={`Export scan ${scan.subnet}`}
                    >
                      <Export size={14} />
                      <span>Export</span>
                    </button>
                    <button
                      data-testid={`delete-scan-${i}`}
                      onClick={() => setDeleteId(scan.id)}
                      className="flex min-h-11 items-center justify-center gap-1.5 rounded-md border border-white/10 px-3 py-2 text-xs font-mono text-danger/70 transition-colors hover:bg-danger/5 hover:text-danger"
                      aria-label={`Delete scan ${scan.subnet}`}
                    >
                      <Trash size={14} />
                      <span>Delete</span>
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
                    <div className="p-3 sm:p-4 max-h-72 overflow-y-auto">
                      <div className="space-y-1">
                        {expandedScan.devices.map((d, j) => (
                          <div
                            key={d.id}
                            className="flex flex-col gap-2 rounded-md px-3 py-3 transition-colors hover:bg-white/[0.03] sm:flex-row sm:items-center sm:justify-between"
                          >
                            <div className="min-w-0 flex flex-wrap items-center gap-x-3 gap-y-1">
                              <span className="font-mono text-xs text-white">{d.ip}</span>
                              <span className="break-all font-mono text-[11px] text-[#636366]">{d.mac}</span>
                              <span className="text-xs text-[#8A8A8E]">{d.vendor}</span>
                            </div>
                            <div className="flex items-center justify-between gap-3 sm:justify-end">
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
              className="min-h-11 px-4 py-2 text-sm border border-white/20 text-white rounded-md hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              data-testid="confirm-delete-btn"
              onClick={deleteScan}
              className="min-h-11 px-4 py-2 text-sm bg-danger text-white rounded-md font-bold hover:bg-[#CC2F26] transition-colors"
            >
              Delete
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
