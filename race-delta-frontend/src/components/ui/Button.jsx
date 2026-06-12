export default function Button({ children, variant = "primary", className = "", ...props }) {
    const baseStyle = "inline-flex items-center justify-center font-black uppercase tracking-[0.12em] rounded-md transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "bg-[#e10600] text-white hover:bg-[#b90500]",
        secondary: "bg-[#16191d] border border-[#3a4048] text-white hover:bg-[#20242a]",
        ghost: "bg-transparent text-[#9ca3af] hover:text-white"
    };

    const size = "px-4 py-2.5 text-xs";

    return (
        <button
            className={`${baseStyle} ${variants[variant]} ${size} ${className}`}
            {...props}
        >
            {children}
        </button>
    );
}
