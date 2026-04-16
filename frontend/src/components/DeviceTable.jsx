import { motion } from "framer-motion";
import {
  Table, TableBody, TableCell, TableHead,
  TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Warning, CheckCircle, Question, VideoCamera } from "@phosphor-icons/react";

function getRiskColor(score) {
  if (score >= 70) return "text-danger";
  if (score >= 40) return "text-[#FF9500]";
  if (score >= 20) return "text-warning";
  return "text-safe";
}

function getRiskBg(score) {
  if (score >= 70) return "bg-danger/20 border-danger/50 text-danger";
  if (score >= 40) return "bg-[#FF9500]/20 border-[#FF9500]/50 text-[#FF9500]";
  if (score >= 20) return "bg-warning/20 border-warning/50 text-warning";
  return "bg-safe/20 border-safe/50 text-safe";
}

function getTypeIcon(type) {
  if (type === "Likely Camera") return <VideoCamera size={16} weight="fill" className="text-danger" />;
  if (type === "Possible Camera") return <Warning size={16} weight="fill" className="text-[#FF9500]" />;
  if (type === "Router" || type === "Printer" || type.includes("Phone") || type.includes("Laptop"))
    return <CheckCircle size={16} weight="fill" className="text-safe" />;
  return <Question size={16} weight="fill" className="text-[#8A8A8E]" />;
}

function getTypeBadge(type) {
  if (type === "Likely Camera") return "bg-danger/20 border border-danger/50 text-danger";
  if (type === "Possible Camera") return "bg-[#FF9500]/20 border border-[#FF9500]/50 text-[#FF9500]";
  return "bg-white/5 border border-white/10 text-[#8A8A8E]";
}

export default function DeviceTable({ devices = [], onDeviceClick }) {
  if (!devices.length) return null;

  return (
    <div data-testid="device-table" className="border border-white/10 bg-surface rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-white/10 hover:bg-transparent">
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4">Status</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4">IP Address</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4 hidden md:table-cell">MAC Address</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4 hidden lg:table-cell">Vendor</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4">Ports</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4">Type</TableHead>
              <TableHead className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E] py-3 px-4 text-right">Risk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {devices.map((device, i) => (
              <motion.tr
                key={device.id}
                data-testid={`device-row-${i}`}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.05 }}
                onClick={() => onDeviceClick?.(device)}
                className="border-b border-white/5 hover:bg-white/[0.03] cursor-pointer transition-colors group"
              >
                <TableCell className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {getTypeIcon(device.device_type)}
                  </div>
                </TableCell>
                <TableCell className="py-3 px-4">
                  <span className="font-mono text-sm text-white">{device.ip}</span>
                </TableCell>
                <TableCell className="py-3 px-4 hidden md:table-cell">
                  <span className="font-mono text-xs text-[#8A8A8E]">{device.mac}</span>
                </TableCell>
                <TableCell className="py-3 px-4 hidden lg:table-cell">
                  <span className="text-sm text-[#8A8A8E]">{device.vendor}</span>
                </TableCell>
                <TableCell className="py-3 px-4">
                  <div className="flex flex-wrap gap-1">
                    {device.open_ports.slice(0, 4).map((port) => (
                      <span
                        key={port}
                        className={`font-mono text-[11px] px-1.5 py-0.5 rounded-sm ${
                          port === 554
                            ? "bg-danger/20 text-danger"
                            : [80, 8080, 8000, 88].includes(port)
                            ? "bg-warning/20 text-warning"
                            : "bg-white/5 text-[#636366]"
                        }`}
                      >
                        {port}
                      </span>
                    ))}
                    {device.open_ports.length > 4 && (
                      <span className="font-mono text-[11px] text-[#636366]">
                        +{device.open_ports.length - 4}
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="py-3 px-4">
                  <Badge className={`rounded-sm text-[11px] px-2 py-0.5 font-mono ${getTypeBadge(device.device_type)}`}>
                    {device.device_type}
                  </Badge>
                </TableCell>
                <TableCell className="py-3 px-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden hidden sm:block">
                      <div
                        className={`h-full rounded-full transition-all ${
                          device.risk_score >= 70 ? "bg-danger" :
                          device.risk_score >= 40 ? "bg-[#FF9500]" :
                          device.risk_score >= 20 ? "bg-warning" : "bg-safe"
                        }`}
                        style={{ width: `${device.risk_score}%` }}
                      />
                    </div>
                    <span className={`font-mono text-sm font-bold ${getRiskColor(device.risk_score)}`}>
                      {device.risk_score}
                    </span>
                  </div>
                </TableCell>
              </motion.tr>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
