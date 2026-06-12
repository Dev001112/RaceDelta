export default function Card({ children, className = "", onClick, ...props }) {
    const baseStyle = "broadcast-panel p-5 relative overflow-hidden";
    const interactiveStyle = onClick
        ? "cursor-pointer transition-colors hover:bg-[#16191d] hover:border-[#3a4048] group"
        : "";

    return (
        <div
            className={`${baseStyle} ${interactiveStyle} ${className}`}
            onClick={onClick}
            {...props}
        >
            {children}
        </div>
    );
}
