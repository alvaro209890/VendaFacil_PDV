import { motion } from "framer-motion";

type MascoteProps = {
  estado?: "normal" | "feliz" | "pensando" | "alerta";
  frase?: string;
};

export default function Mascote({ estado = "normal", frase }: MascoteProps) {
  const isHappy = estado === "feliz";
  const isThinking = estado === "pensando";
  const isAlert = estado === "alerta";

  return (
    <div className="flex flex-col items-center gap-2 group pointer-events-none select-none">
      <motion.div
        animate={{
          y: [0, -5, 0],
          rotate: isHappy ? [0, -5, 5, 0] : 0,
        }}
        transition={{
          y: { repeat: Infinity, duration: 2, ease: "easeInOut" },
          rotate: { repeat: isHappy ? Infinity : 0, duration: 0.5 },
        }}
        className="relative"
      >
        {/* Balão de fala */}
        {frase && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="absolute -top-12 left-1/2 -translate-x-1/2 bg-white text-slate-900 text-[10px] font-bold px-2 py-1 rounded-lg shadow-xl whitespace-nowrap before:content-[''] before:absolute before:top-full before:left-1/2 before:-translate-x-1/2 before:border-8 before:border-transparent before:border-t-white"
          >
            {frase}
          </motion.div>
        )}

        {/* Corpo do Robô/Mascote */}
        <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Cabeça */}
          <rect x="20" y="30" width="60" height="50" rx="12" fill="url(#bodyGradient)" />
          <rect x="20" y="30" width="60" height="50" rx="12" stroke="#3b82f6" strokeWidth="2" />
          
          {/* Antena */}
          <line x1="50" y1="30" x2="50" y2="15" stroke="#3b82f6" strokeWidth="2" />
          <motion.circle
            cx="50"
            cy="15"
            r="4"
            animate={{ fill: isAlert ? "#ef4444" : "#3b82f6" }}
            fill="#3b82f6"
          />

          {/* Olhos/Visor */}
          <rect x="30" y="45" width="40" height="20" rx="6" fill="#1e293b" />
          
          {/* Pupilas */}
          <motion.circle
            animate={{
              x: isThinking ? [0, 5, -5, 0] : 0,
              scaleY: isHappy ? 0.2 : 1,
            }}
            transition={{ x: { repeat: Infinity, duration: 3 } }}
            cx="40" cy="55" r="3" fill="#60a5fa" 
          />
          <motion.circle
            animate={{
              x: isThinking ? [0, 5, -5, 0] : 0,
              scaleY: isHappy ? 0.2 : 1,
            }}
            transition={{ x: { repeat: Infinity, duration: 3 } }}
            cx="60" cy="55" r="3" fill="#60a5fa" 
          />

          <defs>
            <linearGradient id="bodyGradient" x1="50" y1="30" x2="50" y2="80" gradientUnits="userSpaceOnUse">
              <stop stopColor="#1e3a8a" />
              <stop offset="1" stopColor="#1e293b" />
            </linearGradient>
          </defs>
        </svg>

        {/* Brilho nos pés */}
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-8 h-1 bg-brand-500/30 blur-sm rounded-full" />
      </motion.div>
    </div>
  );
}
