import { Box, KeyRound, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import type { APIKey, APIKeyCreated, Product } from '../api'
import { listKeys, listProjectProducts } from '../api'
import CopyableId from '../components/CopyableId'
import CreateKeyModal from '../components/CreateKeyModal'
import KeyRow from '../components/KeyRow'

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>()
  const location = useLocation()
  const { orgName, orgId } = (location.state as { orgName?: string; orgId?: string }) ?? {}

  const [keys, setKeys] = useState<APIKey[]>([])
  const [linkedProducts, setLinkedProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [newKeys, setNewKeys] = useState<Record<string, string>>({})

  useEffect(() => {
    if (!projectId || !orgId) return
    Promise.all([listKeys(projectId), listProjectProducts(projectId)])
      .then(([k, lp]) => { setKeys(k); setLinkedProducts(lp) })
      .finally(() => setLoading(false))
  }, [projectId, orgId])

  const handleCreated = (result: APIKeyCreated) => {
    setKeys(prev => [result.key, ...prev])
    setNewKeys(prev => ({ ...prev, [result.key.id]: result.plaintext }))
    setShowModal(false)
  }

  const handleRevoked = (updated: APIKey) => {
    setKeys(prev => prev.map(k => (k.id === updated.id ? updated : k)))
  }

  const activeCount = keys.filter(k => !k.revoked_at).length

  if (loading) return <div className="p-6 text-[#5f6368] text-sm">Loading…</div>

  return (
    <div className="p-6">
      {/* Breadcrumb / back */}
      <div className="flex items-center gap-2 mb-4 text-sm">
        <Link to="/" className="text-[#1a73e8] hover:underline">Organizations</Link>
        {orgId && orgName && (
          <>
            <span className="text-[#9aa0a6]">/</span>
            <Link to={`/orgs/${orgId}`} className="text-[#1a73e8] hover:underline">{orgName}</Link>
          </>
        )}
        <span className="text-[#9aa0a6]">/</span>
        <span className="text-[#202124] font-medium">API Keys</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-[22px] font-normal text-[#202124] flex items-center gap-2">
            <KeyRound size={20} className="text-[#5f6368]" /> API Keys
          </h1>
          <div className="mt-1">
            <CopyableId label="project-id" value={projectId!} short={false} />
          </div>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 bg-[#1a73e8] hover:bg-[#1557b0] text-white text-sm font-medium px-4 py-2 rounded transition-colors shadow-sm"
        >
          <Plus size={15} /> Create key
        </button>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-6 mb-5">
        <div className="flex items-center gap-2">
          <span className="text-[22px] font-normal text-[#202124]">{activeCount}</span>
          <span className="text-[13px] text-[#5f6368]">active</span>
        </div>
        <div className="w-px h-5 bg-[#dadce0]" />
        <div className="flex items-center gap-2">
          <span className="text-[22px] font-normal text-[#202124]">{keys.length - activeCount}</span>
          <span className="text-[13px] text-[#5f6368]">revoked</span>
        </div>
        {linkedProducts.length > 0 && (
          <>
            <div className="w-px h-5 bg-[#dadce0]" />
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] text-[#5f6368]">Products:</span>
              {linkedProducts.map(p => (
                <span key={p.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full text-[11px]">
                  <Box size={9} /> {p.name}
                </span>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Keys table */}
      {keys.length === 0 ? (
        <div className="bg-white border border-[#dadce0] rounded-lg p-10 text-center">
          <KeyRound size={32} className="text-[#dadce0] mx-auto mb-3" />
          <p className="text-sm font-medium text-[#3c4043]">No API keys</p>
          <p className="text-xs text-[#5f6368] mt-1">Create a key to get started.</p>
        </div>
      ) : (
        <div className="bg-white border border-[#dadce0] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f1f3f4] bg-[#f8f9fa]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Prefix</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Key value</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Scopes</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Product</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Rate limit</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {keys.map(k => (
                <KeyRow
                  key={k.id}
                  apiKey={k}
                  onRevoked={handleRevoked}
                  newPlaintext={newKeys[k.id]}
                  products={linkedProducts}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && projectId && orgId && (
        <CreateKeyModal
          orgId={orgId}
          orgName={orgName ?? ''}
          preselectedProjectId={projectId}
          preselectedProjectName={orgName ?? ''}
          onCreated={handleCreated}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}
