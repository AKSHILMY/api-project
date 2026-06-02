import { Box, CheckCircle, ShieldCheck, XCircle } from 'lucide-react'
import { useState } from 'react'
import type { APIKey } from '../api'
import { verifyKey } from '../api'

export default function VerifyKey() {
  const [input, setInput] = useState('')
  const [result, setResult] = useState<APIKey | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return
    setLoading(true)
    setResult(null)
    setError('')
    try {
      const key = await verifyKey(input.trim())
      setResult(key)
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Invalid key'
      setError(msg || 'Invalid key')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-[22px] font-normal text-[#202124] flex items-center gap-2">
          <ShieldCheck size={20} className="text-[#5f6368]" /> Verify Key
        </h1>
        <p className="text-[13px] text-[#5f6368] mt-0.5">
          Check if an API key is valid and inspect its metadata.
        </p>
      </div>

      <div className="bg-white border border-[#dadce0] rounded-lg p-5">
        <form onSubmit={handleVerify} className="flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="sk_…"
            className="flex-1 border border-[#dadce0] rounded px-3 py-2 font-mono text-sm text-[#202124] placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-[#1a73e8] hover:bg-[#1557b0] disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded transition-colors"
          >
            {loading ? 'Checking…' : 'Verify'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="mt-4 flex items-start gap-3 bg-[#fce8e6] border border-[#f5c6c3] rounded-lg px-4 py-3">
            <XCircle size={16} className="text-[#c5221f] mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-[#c5221f]">Key invalid</p>
              <p className="text-xs text-[#c5221f] mt-0.5 opacity-80">{error}</p>
            </div>
          </div>
        )}

        {/* Success */}
        {result && (
          <div className="mt-4 border border-[#ceead6] rounded-lg overflow-hidden">
            <div className="flex items-center gap-2 bg-[#e6f4ea] px-4 py-3 border-b border-[#ceead6]">
              <CheckCircle size={15} className="text-[#137333]" />
              <span className="text-sm font-medium text-[#137333]">Valid — key is active</span>
            </div>
            <div className="px-4 py-4 grid grid-cols-2 gap-x-6 gap-y-3">
              <div>
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Key ID</p>
                <p className="font-mono text-xs text-[#202124]">{result.id}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Project ID</p>
                <p className="font-mono text-xs text-[#202124]">{result.project_id}</p>
              </div>
              <div>
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Scopes</p>
                {result.metadata.scopes.length > 0 ? (
                  <div className="flex flex-wrap gap-1">
                    {result.metadata.scopes.map(s => (
                      <span key={s} className="px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full text-[11px]">{s}</span>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#9aa0a6]">None</p>
                )}
              </div>
              <div>
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Rate limit</p>
                <p className="text-sm text-[#202124]">
                  {result.metadata.rate_limit
                    ? <>{result.metadata.rate_limit} <span className="text-xs text-[#9aa0a6]">req/min</span></>
                    : <span className="text-[#9aa0a6]">—</span>
                  }
                </p>
              </div>
              {result.product_id && (
                <div>
                  <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Product</p>
                  <p className="flex items-center gap-1 text-xs text-[#202124]">
                    <Box size={11} className="text-[#5f6368]" />
                    <span className="font-mono">{result.product_id.slice(0, 12)}…</span>
                  </p>
                </div>
              )}
              <div>
                <p className="text-[11px] text-[#5f6368] uppercase tracking-wide mb-0.5">Created</p>
                <p className="text-sm text-[#202124]">
                  {new Date(result.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
