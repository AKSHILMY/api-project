import { Box, Braces, Check, Copy, Layers, Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { APIKey, Product } from '../api'
import { revokeKey } from '../api'

interface Props {
  apiKey: APIKey
  onRevoked: (key: APIKey) => void
  newPlaintext?: string
  products?: Product[]
}

export default function KeyRow({ apiKey, onRevoked, newPlaintext, products = [] }: Props) {
  const product = apiKey.product_id ? products.find(p => p.id === apiKey.product_id) : null
  const [revoking, setRevoking] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showCustom, setShowCustom] = useState(false)
  const isRevoked = !!apiKey.revoked_at
  const hasCustom = apiKey.metadata.custom && Object.keys(apiKey.metadata.custom).length > 0

  const handleRevoke = async () => {
    if (!confirm('Revoke this key? This cannot be undone.')) return
    setRevoking(true)
    try {
      const updated = await revokeKey(apiKey.id)
      onRevoked(updated)
    } finally {
      setRevoking(false)
    }
  }

  const handleCopy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <tr className="border-b border-[#f1f3f4] hover:bg-[#f8f9fa] group">
      <td className="px-4 py-3">
        {apiKey.metadata.name && (
          <div className="text-[13px] font-medium text-[#202124] mb-0.5">{apiKey.metadata.name}</div>
        )}
        <div className="font-mono text-xs text-[#5f6368]">sk_{apiKey.key_prefix}…</div>
      </td>
      <td className="px-4 py-3">
        {newPlaintext ? (
          <button
            onClick={() => handleCopy(newPlaintext)}
            title="Click to copy"
            className="flex items-center gap-2 group/key cursor-pointer"
          >
            <span className="font-mono text-xs bg-[#fef7e0] border border-[#f9ab00] text-[#7b5800] px-2 py-1 rounded max-w-[220px] truncate group-hover/key:border-[#f29900]">
              {newPlaintext}
            </span>
            {copied
              ? <Check size={13} className="text-[#34a853] shrink-0" />
              : <Copy size={13} className="text-[#9aa0a6] group-hover/key:text-[#1a73e8] shrink-0" />
            }
            {copied && <span className="text-[11px] text-[#34a853]">Copied!</span>}
          </button>
        ) : (
          <span className="text-[#9aa0a6] text-xs italic">Hidden — copy on creation</span>
        )}
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-col gap-1">
          {apiKey.metadata.scopes.length > 0 ? (
            <div className="flex gap-1 flex-wrap">
              {apiKey.metadata.scopes.map(s => (
                <span key={s} className="px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full text-[11px] font-medium">
                  {s}
                </span>
              ))}
            </div>
          ) : (
            <span className="text-[#9aa0a6] text-xs">—</span>
          )}
          {hasCustom && (
            <div className="relative">
              <button
                onClick={() => setShowCustom(v => !v)}
                className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#fef7e0] border border-[#f9ab00] text-[#7b5800] rounded text-[11px] hover:border-[#f29900] transition-colors"
              >
                <Braces size={9} /> custom
              </button>
              {showCustom && (
                <div className="absolute left-0 top-6 z-10 bg-white border border-[#dadce0] rounded-lg shadow-lg p-3 min-w-[200px] max-w-[320px]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-medium text-[#5f6368] uppercase tracking-wider">Custom metadata</span>
                    <button onClick={() => setShowCustom(false)} className="text-[#9aa0a6] hover:text-[#3c4043] text-xs">✕</button>
                  </div>
                  <div className="space-y-1">
                    {Object.entries(apiKey.metadata.custom).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-[12px]">
                        <span className="text-[#5f6368] font-mono shrink-0">{k}:</span>
                        <span className="text-[#202124] font-mono break-all">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        {product ? (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full text-[11px] font-medium">
            <Box size={9} /> {product.name}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#f1f3f4] text-[#5f6368] rounded-full text-[11px]">
            <Layers size={9} /> All products
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-[13px] text-[#3c4043]">
        {apiKey.metadata.rate_limit
          ? <span>{apiKey.metadata.rate_limit}<span className="text-[#9aa0a6] text-xs ml-0.5">req/min</span></span>
          : <span className="text-[#9aa0a6]">—</span>}
      </td>
      <td className="px-4 py-3">
        {isRevoked ? (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#fce8e6] text-[#c5221f]">
            Revoked
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#e6f4ea] text-[#137333]">
            Active
          </span>
        )}
      </td>
      <td className="px-4 py-3 text-xs text-[#5f6368]">
        {new Date(apiKey.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
      </td>
      <td className="px-4 py-3 text-right">
        {!isRevoked && (
          <button
            onClick={handleRevoke}
            disabled={revoking}
            className="opacity-0 group-hover:opacity-100 inline-flex items-center gap-1 text-[11px] text-[#c5221f] hover:bg-[#fce8e6] px-2 py-1 rounded transition-all disabled:opacity-40"
          >
            <Trash2 size={12} />
            {revoking ? 'Revoking…' : 'Revoke'}
          </button>
        )}
      </td>
    </tr>
  )
}
