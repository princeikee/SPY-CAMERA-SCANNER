import { motion } from "framer-motion";

export default function MetricCard({ icon: Icon, label, value, color = "scan", delay = 0, testId }) {
  const colorMap = {
    scan: { bg: "bg-scan/10", text: "text-scan", border: "border-scan/20" },
    danger: { bg: "bg-danger/10", text: "text-danger", border: "border-danger/20" },
    warning: { bg: "bg-warning/10", text: "text-warning", border: "border-warning/20" },
    safe: { bg: "bg-safe/10", text: "text-safe", border: "border-safe/20" },
  };
  const c = colorMap[color] || colorMap.scan;

  return (
    <motion.div
      data-testid={testId}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay }}
      className={`border border-white/10 bg-surface rounded-lg p-5 flex flex-col gap-3 hover:border-white/20 transition-colors`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono uppercase tracking-[0.2em] text-[#8A8A8E]">
          {label}
        </span>
        <div className={`w-8 h-8 rounded-md ${c.bg} flex items-center justify-center`}>
          <Icon size={18} weight="duotone" className={c.text} />
        </div>
      </div>
      <div className={`text-3xl font-heading font-black ${c.text} tracking-tight`}>
        {value}
      </div>
    </motion.div>
  );
}
