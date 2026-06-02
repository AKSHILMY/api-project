import { Building2, ChevronRight, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { Organization } from '../api'
import { createOrg, listOrgs } from '../api'
import CopyableId from '../components/CopyableId'

export default function Home() {
  const [orgs, setOrgs] = useState<Organization[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listOrgs().then(setOrgs).finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    setError('')
    try {
      const org = await createOrg(newName.trim())
      setOrgs(prev => [org, ...prev])
      setNewName('')
      setShowForm(false)
    } catch {
      setError('Failed to create organization')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl">
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-normal text-[#202124]">Organizations</h1>
          <p className="text-[13px] text-[#5f6368] mt-0.5">
            {loading ? '…' : `${orgs.length} organization${orgs.length !== 1 ? 's' : ''}`}
          </p>
        </div>
        <button
          onClick={() => setShowForm(v => !v)}
          className="flex items-center gap-1.5 bg-[#1a73e8] hover:bg-[#1557b0] text-white text-sm font-medium px-4 py-2 rounded transition-colors shadow-sm"
        >
          <Plus size={16} />
          New organization
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="mb-6 bg-white border border-[#dadce0] rounded-lg p-5">
          <h2 className="text-sm font-medium text-[#202124] mb-3">Create organization</h2>
          <form onSubmit={handleCreate} className="flex gap-3 items-start">
            <div className="flex-1">
              <input
                autoFocus
                value={newName}
                onChange={e => setNewName(e.target.value)}
                placeholder="Organization name"
                className="w-full border border-[#dadce0] rounded px-3 py-2 text-sm text-[#202124] placeholder-[#9aa0a6] focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
              />
              {error && <p className="text-[#c5221f] text-xs mt-1">{error}</p>}
            </div>
            <button
              type="submit"
              disabled={creating || !newName.trim()}
              className="bg-[#1a73e8] hover:bg-[#1557b0] disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded transition-colors"
            >
              {creating ? 'Creating…' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); setNewName('') }}
              className="border border-[#dadce0] text-[#3c4043] text-sm px-4 py-2 rounded hover:bg-[#f1f3f4] transition-colors"
            >
              Cancel
            </button>
          </form>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="bg-white border border-[#dadce0] rounded-lg p-8 text-center text-[#5f6368] text-sm">
          Loading…
        </div>
      ) : orgs.length === 0 ? (
        <div className="bg-white border border-[#dadce0] rounded-lg p-12 text-center">
          <Building2 size={36} className="text-[#dadce0] mx-auto mb-3" />
          <p className="text-[#3c4043] text-sm font-medium">No organizations yet</p>
          <p className="text-[#5f6368] text-xs mt-1">Create your first organization to get started.</p>
        </div>
      ) : (
        <div className="bg-white border border-[#dadce0] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#f1f3f4]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Created</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {orgs.map(org => (
                <tr key={org.id} className="border-b border-[#f1f3f4] last:border-0 hover:bg-[#f8f9fa] group">
                  <td className="px-4 py-3">
                    <Link
                      to={`/orgs/${org.id}`}
                      className="flex items-center gap-2 text-[#1a73e8] hover:underline font-medium text-sm"
                    >
                      <Building2 size={14} className="text-[#5f6368]" />
                      {org.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><CopyableId label="org-id" value={org.id} /></td>
                  <td className="px-4 py-3 text-xs text-[#5f6368]">
                    {new Date(org.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/orgs/${org.id}`}
                      className="opacity-0 group-hover:opacity-100 inline-flex items-center gap-1 text-xs text-[#1a73e8] hover:underline transition-opacity"
                    >
                      View <ChevronRight size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
