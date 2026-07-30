export function Badge({ children, variant = 'default', className = "" }: { children: React.ReactNode, variant?: 'default' | 'risk' | 'entity' | 'keyword' | 'jargon' | 'concept', className?: string }) {
    const variants = {
        default: "bg-white/10 text-white",
        risk: "bg-red-500/20 text-red-500 border border-red-500/30",
        entity: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
        keyword: "bg-yellow-500/20 text-yellow-500 border border-yellow-500/30",
        jargon: "bg-teal-500/20 text-teal-400 border border-teal-500/30",
        concept: "bg-purple-500/20 text-purple-400 border border-purple-500/30",
    }

    return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${variants[variant]} ${className}`}>
            {children}
        </span>
    )
}
