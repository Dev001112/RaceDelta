import { motion } from "framer-motion";

export default function Button({ children, variant = "primary", className = "", ...props }) {
    const baseStyle = "inline-flex items-center justify-center font-semibold rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-cyan-500 text-black hover:bg-cyan-400 shadow-[0_0_15px_rgba(6,182,212,0.4)] hover:shadow-[0_0_25px_rgba(6,182,212,0.6)]",
        secondary: "bg-white/5 border border-white/10 text-white hover:bg-white/10 hover:border-white/20",
        ghost: "bg-transparent text-slate-400 hover:text-white"
    };

    const size = "px-5 py-2.5 text-sm";

    return (
        <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`${baseStyle} ${variants[variant]} ${size} ${className}`}
            {...props}
        >
            {children}
        </motion.button>
    );
}
