export default function Card({ children, className = "", onClick, ...props }) {
    // Base glass style
    const baseStyle = "bg-white/[0.03] border border-white/[0.05] rounded-xl backdrop-blur-md p-6 relative overflow-hidden";

    // Interactive style if onClick is present
    const interactiveStyle = onClick
        ? "cursor-pointer transition-all duration-300 hover:bg-white/[0.06] hover:border-white/[0.1] hover:shadow-[0_0_25px_rgba(6,182,212,0.15)] group"
        : "";

    return (
        <div
            className={`${baseStyle} ${interactiveStyle} ${className}`}
            onClick={onClick}
            {...props}
        >
            {/* Subtle shine effect on hover */}
            {onClick && (
                <div className="absolute inset-0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700 bg-gradient-to-r from-transparent via-white/[0.05] to-transparent pointer-events-none" />
            )}
            {children}
        </div>
    );
}
