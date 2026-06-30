import {
  Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Warning, ShieldCheck, VideoCamera, WifiHigh,
  Globe, Lock, Desktop, ArrowSquareOut,
} from "@phosphor-icons/react";

function getRiskLevel(score) {
  if (score >= 70) return { label: "CRITICAL", color: "text-danger", bg: "bg-danger", barColor: "bg-danger" };
  if (score >= 40) return { label: "HIGH", color: "text-[#FF9500]", bg: "bg-[#FF9500]", barColor: "bg-[#FF9500]" };
  if (score >= 20) return { label: "MEDIUM", color: "text-warning", bg: "bg-warning", barColor: "bg-warning" };
  return { label: "LOW", color: "text-safe", bg: "bg-safe", barColor: "bg-safe" };
}

function PortItem({ port }) {
  const known = {
    80: { name: "HTTP", icon: Globe, risk: "medium" },
    443: { name: "HTTPS", icon: Lock, risk: "low" },
    554: { name: "RTSP", icon: VideoCamera, risk: "critical" },
    8080: { name: "HTTP-ALT", icon: Globe, risk: "medium" },
    8000: { name: "HTTP-ALT", icon: Globe, risk: "medium" },
    88: { name: "HTTP-ALT", icon: Globe, risk: "medium" },
    53: { name: "DNS", icon: WifiHigh, risk: "low" },
    445: { name: "SMB", icon: Desktop, risk: "low" },
    139: { name: "NetBIOS", icon: Desktop, risk: "low" },
    631: { name: "IPP", icon: Desktop, risk: "low" },
    9100: { name: "Print", icon: Desktop, risk: "low" },
    37777: { name: "Dahua-DVR", icon: VideoCamera, risk: "critical" },
    8200: { name: "Hikv-SDK", icon: VideoCamera, risk: "high" },
    9000: { name: "Cam-Ctrl", icon: VideoCamera, risk: "high" },
    2020: { name: "Cam-P2P", icon: VideoCamera, risk: "high" },
    5000: { name: "NAS-UI", icon: Desktop, risk: "low" },
    5001: { name: "NAS-SSL", icon: Lock, risk: "low" },
    62078: { name: "iDevice", icon: Desktop, risk: "low" },
    5060: { name: "SIP", icon: Desktop, risk: "low" },
    8443: { name: "HTTPS-ALT", icon: Lock, risk: "low" },
    9080: { name: "HTTP-ALT", icon: Globe, risk: "medium" },
    9295: { name: "Remote", icon: Desktop, risk: "low" },
    9296: { name: "Remote", icon: Desktop, risk: "low" },
  };

  const info = known[port] || { name: `Port ${port}`, icon: WifiHigh, risk: "low" };
  const riskColors = {
    critical: "bg-danger/20 border-danger/40 text-danger",
    high: "bg-[#FF9500]/20 border-[#FF9500]/40 text-[#FF9500]",
    medium: "bg-warning/20 border-warning/40 text-warning",
    low: "bg-white/5 border-white/10 text-[#8A8A8E]",
  };

  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-md border ${riskColors[info.risk]}`}>
      <info.icon size={14} weight="duotone" />
      <span className="font-mono text-xs">{port}</span>
      <span className="text-[10px] uppercase tracking-wider opacity-70">{info.name}</span>
    </div>
  );
}

export default function DeviceSheet({ device, open, onClose }) {
  if (!device) return null;

  const risk = getRiskLevel(device.risk_score);
  const services = device.services || [];

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-md bg-surface border-l border-white/10 overflow-y-auto p-0"
      >
        <div className="p-6">
          <SheetHeader>
            <div className="flex items-center gap-3 mb-1">
              {device.device_type.includes("Camera") ? (
                <VideoCamera size={24} weight="duotone" className="text-danger" />
              ) : (
                <ShieldCheck size={24} weight="duotone" className="text-safe" />
              )}
              <SheetTitle className="font-heading font-bold text-lg text-white">
                Device Details
              </SheetTitle>
            </div>
            <SheetDescription className="text-[#8A8A8E] text-sm">
              Full analysis of network device
            </SheetDescription>
          </SheetHeader>

          {/* Risk Score Hero */}
          <div data-testid="device-risk-score" className="mt-6 p-4 rounded-lg border border-white/10 bg-app">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E]">
                Risk Score
              </span>
              <Badge className={`rounded-sm font-mono text-xs px-2 ${
                risk.label === "CRITICAL" ? "bg-danger/20 border border-danger/50 text-danger" :
                risk.label === "HIGH" ? "bg-[#FF9500]/20 border border-[#FF9500]/50 text-[#FF9500]" :
                risk.label === "MEDIUM" ? "bg-warning/20 border border-warning/50 text-warning" :
                "bg-safe/20 border border-safe/50 text-safe"
              }`}>
                {risk.label}
              </Badge>
            </div>
            <div className={`text-5xl font-heading font-black ${risk.color} mb-3`}>
              {device.risk_score}
            </div>
            <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${risk.barColor} transition-all duration-500`}
                style={{ width: `${device.risk_score}%` }}
              />
            </div>
          </div>

          {/* Device Info */}
          <div className="mt-6 space-y-3">
            <h4 className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] mb-2">
              Device Information
            </h4>
            {[
              { label: "IP Address", value: device.ip, mono: true },
              { label: "MAC Address", value: device.mac, mono: true },
              { label: "Vendor", value: device.vendor },
              { label: "Model", value: device.model || "Unknown" },
              { label: "Hostname", value: device.hostname || "N/A" },
              { label: "Device Type", value: device.device_type },
              { label: "Scan Engine", value: device.scan_engine || "tcp-connect" },
            ].map((row) => (
              <div key={row.label} className="flex items-center justify-between py-2 border-b border-white/5">
                <span className="text-xs text-[#636366] uppercase tracking-wider">{row.label}</span>
                <span className={`text-sm text-white ${row.mono ? "font-mono" : ""}`}>{row.value}</span>
              </div>
            ))}
          </div>

          {/* Open Ports */}
          <div className="mt-6">
            <h4 className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] mb-3">
              Open Ports ({device.open_ports.length})
            </h4>
            <div className="grid grid-cols-2 gap-2">
              {device.open_ports.map((port) => (
                <PortItem key={port} port={port} />
              ))}
            </div>
          </div>

          {services.length > 0 && (
            <div className="mt-6">
              <h4 className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] mb-3">
                Service Fingerprints
              </h4>
              <div className="space-y-2">
                {services.map((service) => (
                  <div key={`${service.port}-${service.service}`} className="p-3 rounded-md bg-app border border-white/10">
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Badge className="rounded-sm text-[10px] px-1.5 py-0 font-mono bg-white/5 border border-white/10 text-white">
                          {service.port}/tcp
                        </Badge>
                        <span className="text-sm text-white font-medium">{service.service}</span>
                      </div>
                      {service.product && (
                        <span className="text-xs text-[#8A8A8E] font-mono">{service.product}</span>
                      )}
                    </div>
                    {service.banner && (
                      <div className="mt-2 text-xs text-[#8A8A8E] font-mono break-words">
                        {service.banner}
                      </div>
                    )}
                    {service.notes?.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {service.notes.map((note) => (
                          <div key={note} className="text-[11px] text-[#636366] font-mono">
                            {note}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Risk Factors */}
          {device.risk_factors?.length > 0 && (
            <div className="mt-6">
              <h4 className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] mb-3">
                Risk Factors
              </h4>
              <div className="space-y-2">
                {device.risk_factors.map((factor, i) => (
                  <div key={i} className="flex items-start gap-2 p-3 rounded-md bg-danger/5 border border-danger/10">
                    <Warning size={14} weight="fill" className="text-danger mt-0.5 flex-shrink-0" />
                    <span className="text-xs text-[#8A8A8E] font-mono leading-relaxed">{factor}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="mt-6 pt-4 border-t border-white/5">
            <div className="flex justify-between text-xs text-[#636366]">
              <span>First Seen</span>
              <span className="font-mono">
                {new Date(device.first_seen).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
