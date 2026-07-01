import { NavLink } from "react-router-dom";
import { Crosshair, ClockCounterClockwise, ShieldWarning, WifiHigh } from "@phosphor-icons/react";

const navItems = [
  { to: "/", icon: Crosshair, label: "Scanner" },
  { to: "/history", icon: ClockCounterClockwise, label: "History" },
];

export default function Sidebar() {
  return (
    <aside
      data-testid="sidebar-nav"
      className="fixed inset-x-0 bottom-0 z-40 flex bg-surface/95 border-t border-white/10 pb-[env(safe-area-inset-bottom)] backdrop-blur md:inset-y-0 md:left-0 md:right-auto md:w-16 md:flex-col md:border-r md:border-t-0 md:pb-0 lg:w-56"
    >
      {/* Logo */}
      <div className="hidden md:flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <div className="w-8 h-8 rounded-md bg-scan/20 flex items-center justify-center flex-shrink-0">
          <ShieldWarning size={20} weight="duotone" className="text-scan" />
        </div>
        <div className="hidden lg:block">
          <h1 className="font-heading font-black text-sm tracking-tight text-white leading-none">
            SPYCAM
          </h1>
          <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#8A8A8E] leading-none mt-0.5">
            SCANNER
          </p>
        </div>
      </div>

      {/* Nav */}
      <nav className="grid w-full grid-cols-2 gap-1 px-2 py-2 md:flex md:flex-1 md:flex-col md:space-y-1 md:py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-testid={`nav-${item.label.toLowerCase()}`}
            className={({ isActive }) =>
              `flex min-h-14 items-center justify-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors md:min-h-11 md:justify-start md:text-sm ${
                isActive
                  ? "bg-scan/10 text-scan border border-scan/20"
                  : "text-[#8A8A8E] hover:bg-white/5 hover:text-white border border-transparent"
              }`
            }
            end
          >
            <item.icon size={20} weight="duotone" className="flex-shrink-0" />
            <span className="md:hidden lg:block">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="hidden px-3 py-4 border-t border-white/10 md:block">
        <div className="flex items-center gap-2">
          <WifiHigh size={16} weight="duotone" className="text-safe flex-shrink-0" />
          <span className="hidden lg:block text-xs font-mono text-safe">ONLINE</span>
        </div>
      </div>
    </aside>
  );
}
