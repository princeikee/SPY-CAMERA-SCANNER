import { motion } from "framer-motion";
import { ShieldWarning } from "@phosphor-icons/react";

export default function ScanAnimation({ progress = 0 }) {
  return (
    <div data-testid="scan-animation" className="relative w-48 h-48 mx-auto">
      {/* Outer ring */}
      <div className="absolute inset-0 rounded-full border-2 border-scan/20" />

      {/* Pulse rings */}
      {[0, 0.5, 1].map((d, i) => (
        <motion.div
          key={i}
          className="absolute inset-2 rounded-full border border-scan/30"
          animate={{ scale: [0.8, 1.3], opacity: [0.6, 0] }}
          transition={{ duration: 2, delay: d, repeat: Infinity, ease: "easeOut" }}
        />
      ))}

      {/* Sweep line */}
      <motion.div
        className="absolute top-1/2 left-1/2 w-1/2 h-[2px] origin-left"
        style={{
          background: "linear-gradient(90deg, #007AFF 0%, transparent 100%)",
          marginTop: "-1px",
        }}
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      />

      {/* Center icon */}
      <div className="absolute inset-0 flex items-center justify-center">
        <motion.div
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1.5, repeat: Infinity }}
        >
          <ShieldWarning size={36} weight="duotone" className="text-scan" />
        </motion.div>
      </div>

      {/* Progress text */}
      <div className="absolute -bottom-8 left-0 right-0 text-center">
        <span className="font-mono text-sm text-scan">{progress}%</span>
      </div>
    </div>
  );
}
