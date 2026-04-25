import { useState } from 'react';
import { restartService, scaleService, triggerProcess } from '../api/client';

export default function ActionPanel({ onAction }) {
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);

    const exec = async (label, fn) => {
        setLoading(true);
        setResult(null);
        try {
            const r = await fn();
            setResult({ ok: true, text: `${label}: ${JSON.stringify(r).substring(0, 200)}` });
        } catch (e) {
            setResult({ ok: false, text: `${label}: ${e.message?.substring(0, 200)}` });
        }
        setLoading(false);
        if (onAction) onAction();
    };

    return (
        <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
                <button disabled={loading} onClick={() => exec('Normal Request', () => triggerProcess())}
                    className="px-3 py-2 text-sm rounded bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50">
                    🚀 Send Normal Request
                </button>
                <button disabled={loading} onClick={() => exec('Burst Errors', async () => { for (let i = 0; i < 4; i++) { await triggerProcess('error', 'service-c').catch(() => { }); } return { sent: 4 }; })}
                    className="px-3 py-2 text-sm rounded bg-red-600 hover:bg-red-700 text-white disabled:opacity-50">
                    💥 Burst 4 Errors (C)
                </button>
                <button disabled={loading} onClick={() => exec('Latency Burst', async () => { for (let i = 0; i < 3; i++) { await triggerProcess('high_latency', 'service-c'); } return { sent: 3 }; })}
                    className="px-3 py-2 text-sm rounded bg-yellow-600 hover:bg-yellow-700 text-white disabled:opacity-50">
                    🐌 Burst Latency (C)
                </button>
            </div>
            <div className="flex flex-wrap gap-2">
                {['service-a', 'service-b', 'service-c'].map(s => (
                    <button key={s} disabled={loading} onClick={() => exec(`Restart ${s}`, () => restartService(s))}
                        className="px-3 py-1.5 text-xs rounded bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50">
                        🔄 Restart {s}
                    </button>
                ))}
                {['service-a', 'service-b', 'service-c'].map(s => (
                    <button key={`scale-${s}`} disabled={loading} onClick={() => exec(`Scale ${s}`, () => scaleService(s, 3))}
                        className="px-3 py-1.5 text-xs rounded bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-50">
                        ⬆️ Scale {s}
                    </button>
                ))}
            </div>
            {result && (
                <div className={`text-xs p-2 rounded ${result.ok ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'}`}>
                    {result.text}
                </div>
            )}
        </div>
    );
}