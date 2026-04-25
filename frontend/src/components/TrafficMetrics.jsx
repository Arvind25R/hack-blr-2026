export default function TrafficMetrics({ logs }) {
    if (!logs || logs.length === 0) return null;

    const total = logs.length;
    const errors = logs.filter(l => l.status === 'ERROR').length;
    const success = logs.filter(l => l.status === 'SUCCESS').length;
    const latency = logs.filter(l => l.status === 'LATENCY').length;
    const avgDuration = logs.filter(l => l.duration_ms > 0).reduce((sum, l) => sum + l.duration_ms, 0) / (logs.filter(l => l.duration_ms > 0).length || 1);
    const errorRate = total > 0 ? ((errors / total) * 100).toFixed(1) : 0;

    const metrics = [
        { label: 'Total Requests', value: total, color: 'text-blue-400' },
        { label: 'Success', value: success, color: 'text-green-400' },
        { label: 'Errors', value: errors, color: 'text-red-400' },
        { label: 'Latency Issues', value: latency, color: 'text-yellow-400' },
        { label: 'Avg Duration', value: `${avgDuration.toFixed(0)}ms`, color: 'text-purple-400' },
        { label: 'Error Rate', value: `${errorRate}%`, color: errorRate > 50 ? 'text-red-400' : 'text-green-400' },
    ];

    return (
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {metrics.map(m => (
                <div key={m.label} className="bg-slate-800/50 rounded-lg p-3 text-center border border-slate-700">
                    <p className={`text-xl font-bold ${m.color}`}>{m.value}</p>
                    <p className="text-xs text-slate-500">{m.label}</p>
                </div>
            ))}
        </div>
    );
}