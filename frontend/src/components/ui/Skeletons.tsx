/**
 * FIX-14: Skeleton Loaders — Reemplazan spinners genéricos con
 * placeholders de layout que mantienen la estructura visual durante la carga.
 */

export const SkeletonCard = ({ className = '' }: { className?: string }) => (
    <div className={`bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 animate-pulse ${className}`}>
        <div className="h-4 w-24 bg-slate-800 rounded-lg mb-4" />
        <div className="h-8 w-32 bg-slate-800 rounded-lg" />
    </div>
);

export const SkeletonChart = ({ className = '' }: { className?: string }) => (
    <div className={`bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 animate-pulse ${className}`}>
        <div className="h-4 w-48 bg-slate-800 rounded-lg mb-6" />
        <div className="flex items-end gap-1 h-[300px] pt-8">
            {Array.from({ length: 40 }).map((_, i) => (
                <div
                    key={i}
                    className="flex-1 bg-slate-800/60 rounded-t-sm transition-all"
                    style={{ height: `${15 + Math.sin(i * 0.5) * 25 + Math.random() * 20}%` }}
                />
            ))}
        </div>
    </div>
);

export const SkeletonTable = ({ rows = 5, className = '' }: { rows?: number; className?: string }) => (
    <div className={`bg-slate-900/50 border border-slate-800/50 rounded-3xl p-6 animate-pulse ${className}`}>
        <div className="h-4 w-48 bg-slate-800 rounded-lg mb-6" />
        <div className="space-y-3">
            {Array.from({ length: rows }).map((_, i) => (
                <div key={i} className="flex gap-4">
                    <div className="h-4 w-16 bg-slate-800 rounded" />
                    <div className="h-4 flex-1 bg-slate-800/40 rounded" />
                    <div className="h-4 w-20 bg-slate-800 rounded" />
                </div>
            ))}
        </div>
    </div>
);
