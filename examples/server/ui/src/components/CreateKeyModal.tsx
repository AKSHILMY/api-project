import { ChevronRight, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { APIKeyCreated, Product, Project } from '../api'
import { createKey, listProjectProducts, listProjects } from '../api'

interface Props {
  orgId: string
  orgName: string
  preselectedProjectId?: string
  preselectedProjectName?: string
  onCreated: (result: APIKeyCreated) => void
  onClose: () => void
}

export default function CreateKeyModal({
  orgId,
  orgName,
  preselectedProjectId,
  preselectedProjectName,
  onCreated,
  onClose,
}: Props) {
  const [projects, setProjects] = useState<Project[]>([])
  const [products, setProducts] = useState<Product[]>([])

  const [selectedProjectId, setSelectedProjectId] = useState(preselectedProjectId ?? '')
  const [selectedProjectName, setSelectedProjectName] = useState(preselectedProjectName ?? '')
  const [selectedProductId, setSelectedProductId] = useState('')
  const [selectedProductName, setSelectedProductName] = useState('')

  const [keyName, setKeyName] = useState('')
  const [scopes, setScopes] = useState('')
  const [rateLimit, setRateLimit] = useState('')
  const [customJson, setCustomJson] = useState('')
  const [customJsonError, setCustomJsonError] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Load projects once
  useEffect(() => {
    listProjects(orgId).then(setProjects)
  }, [orgId])

  // Load products when project changes
  useEffect(() => {
    if (!selectedProjectId) { setProducts([]); setSelectedProductId(''); return }
    listProjectProducts(selectedProjectId).then(setProducts)
    setSelectedProductId('')
    setSelectedProductName('')
  }, [selectedProjectId])

  const handleProjectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value
    const name = projects.find(p => p.id === id)?.name ?? ''
    setSelectedProjectId(id)
    setSelectedProjectName(name)
  }

  const handleProductChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value
    const name = products.find(p => p.id === id)?.name ?? ''
    setSelectedProductId(id)
    setSelectedProductName(name)
  }

  const scopeType = selectedProductId
    ? 'Product-scoped'
    : selectedProjectId
      ? 'Project-scoped'
      : 'Org-wide'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setCustomJsonError('')
    let custom: Record<string, unknown> = {}
    if (customJson.trim()) {
      try {
        custom = JSON.parse(customJson)
        if (typeof custom !== 'object' || Array.isArray(custom)) throw new Error()
      } catch {
        setCustomJsonError('Must be a valid JSON object, e.g. {"user_id": "u_123"}')
        return
      }
    }
    setLoading(true)
    setError('')
    try {
      const result = await createKey({
        org_id: orgId,
        project_id: selectedProjectId || undefined,
        product_id: selectedProductId || undefined,
        name: keyName.trim() || undefined,
        scopes: scopes.split(',').map(s => s.trim()).filter(Boolean),
        rate_limit: rateLimit ? parseInt(rateLimit) : undefined,
        custom,
      })
      onCreated(result)
    } catch (err: unknown) {
      const msg = err && typeof err === 'object' && 'response' in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : 'Failed to create key'
      setError(msg || 'Failed to create key')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-lg border border-[#dadce0]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#dadce0]">
          <h2 className="text-base font-medium text-[#202124]">Create API key</h2>
          <button onClick={onClose} className="text-[#5f6368] hover:text-[#202124] p-1 rounded hover:bg-[#f1f3f4]">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-5">
          {/* Scope path */}
          <div>
            <label className="block text-[13px] font-medium text-[#3c4043] mb-2">Scope</label>

            {/* Breadcrumb path display */}
            <div className="flex items-center gap-1.5 mb-3 px-3 py-2 bg-[#f8f9fa] rounded border border-[#dadce0] text-[13px]">
              <span className="text-[#1a73e8] font-medium">{orgName}</span>
              {selectedProjectId && (
                <>
                  <ChevronRight size={13} className="text-[#9aa0a6]" />
                  <span className="text-[#1a73e8] font-medium">{selectedProjectName}</span>
                </>
              )}
              {selectedProductId && (
                <>
                  <ChevronRight size={13} className="text-[#9aa0a6]" />
                  <span className="text-[#1a73e8] font-medium">{selectedProductName}</span>
                </>
              )}
              <span className="ml-auto text-[11px] px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full font-medium">
                {scopeType}
              </span>
            </div>

            {/* Project selector */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-[12px] text-[#5f6368] w-16 shrink-0">Project</label>
                <select
                  value={selectedProjectId}
                  onChange={handleProjectChange}
                  disabled={!!preselectedProjectId}
                  className="flex-1 border border-[#dadce0] rounded px-2 py-1.5 text-sm text-[#202124] bg-white focus:outline-none focus:border-[#1a73e8] disabled:bg-[#f8f9fa] disabled:text-[#5f6368]"
                >
                  <option value="">— Org-wide (no project restriction)</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {/* Product selector — only shown when project is selected */}
              {selectedProjectId && (
                <div className="flex items-center gap-2">
                  <label className="text-[12px] text-[#5f6368] w-16 shrink-0">Product</label>
                  <select
                    value={selectedProductId}
                    onChange={handleProductChange}
                    className="flex-1 border border-[#dadce0] rounded px-2 py-1.5 text-sm text-[#202124] bg-white focus:outline-none focus:border-[#1a73e8]"
                  >
                    <option value="">— All products in project</option>
                    {products.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Key name */}
          <div>
            <label className="block text-[13px] font-medium text-[#3c4043] mb-1.5">
              Key name
              <span className="ml-1.5 text-[#5f6368] font-normal">optional</span>
            </label>
            <input
              value={keyName}
              onChange={e => setKeyName(e.target.value)}
              placeholder="e.g. Production key"
              className="w-full border border-[#dadce0] rounded px-3 py-2 text-sm placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
            />
          </div>

          {/* Scopes */}
          <div>
            <label className="block text-[13px] font-medium text-[#3c4043] mb-1.5">
              Scopes
              <span className="ml-1.5 text-[#5f6368] font-normal">comma-separated</span>
            </label>
            <input
              value={scopes}
              onChange={e => setScopes(e.target.value)}
              placeholder="read, write, admin"
              className="w-full border border-[#dadce0] rounded px-3 py-2 text-sm placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
            />
          </div>

          {/* Rate limit */}
          <div>
            <label className="block text-[13px] font-medium text-[#3c4043] mb-1.5">
              Rate limit
              <span className="ml-1.5 text-[#5f6368] font-normal">requests / min (optional)</span>
            </label>
            <input
              value={rateLimit}
              onChange={e => setRateLimit(e.target.value)}
              type="number"
              min="1"
              placeholder="e.g. 1000"
              className="w-full border border-[#dadce0] rounded px-3 py-2 text-sm placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
            />
          </div>

          {/* Custom metadata */}
          <div>
            <label className="block text-[13px] font-medium text-[#3c4043] mb-1.5">
              Custom metadata
              <span className="ml-1.5 text-[#5f6368] font-normal">JSON object, optional</span>
            </label>
            <textarea
              value={customJson}
              onChange={e => { setCustomJson(e.target.value); setCustomJsonError('') }}
              placeholder={'{"user_id": "u_123", "plan": "pro"}'}
              rows={3}
              className="w-full border border-[#dadce0] rounded px-3 py-2 text-sm font-mono placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8] resize-none"
            />
            {customJsonError && (
              <p className="text-[12px] text-[#c5221f] mt-1">{customJsonError}</p>
            )}
          </div>

          {error && (
            <div className="text-[13px] text-[#c5221f] bg-[#fce8e6] rounded px-3 py-2">{error}</div>
          )}

          <div className="flex gap-3 pt-1">
            <button
              type="submit"
              disabled={loading}
              className="bg-[#1a73e8] hover:bg-[#1557b0] disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded transition-colors"
            >
              {loading ? 'Creating…' : 'Create'}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="border border-[#dadce0] text-[#3c4043] text-sm font-medium px-5 py-2 rounded hover:bg-[#f1f3f4] transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
