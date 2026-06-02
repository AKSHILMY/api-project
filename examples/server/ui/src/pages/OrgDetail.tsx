import { Box, ChevronRight, FolderOpen, KeyRound, Link2, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { APIKeyCreated, Organization, Product, Project } from '../api'
import CopyableId from '../components/CopyableId'
import CreateKeyModal from '../components/CreateKeyModal'
import {
  createProduct,
  createProject,
  getOrg,
  linkProductToProject,
  listProducts,
  listProjectProducts,
  listProjects,
} from '../api'

interface ProjectWithProducts extends Project {
  linkedProducts: Product[]
  linking: boolean
  selectedProductId: string
}

export default function OrgDetail() {
  const { orgId } = useParams<{ orgId: string }>()
  const [org, setOrg] = useState<Organization | null>(null)
  const [projects, setProjects] = useState<ProjectWithProducts[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)

  const [newProject, setNewProject] = useState('')
  const [newProduct, setNewProduct] = useState('')
  const [creatingProject, setCreatingProject] = useState(false)
  const [creatingProduct, setCreatingProduct] = useState(false)
  const [showProjectForm, setShowProjectForm] = useState(false)
  const [showProductForm, setShowProductForm] = useState(false)
  const [showKeyModal, setShowKeyModal] = useState(false)

  useEffect(() => {
    if (!orgId) return
    Promise.all([getOrg(orgId), listProjects(orgId), listProducts(orgId)])
      .then(async ([o, prjs, prds]) => {
        setOrg(o)
        setProducts(prds)
        const withProducts = await Promise.all(
          prjs.map(async p => ({
            ...p,
            linkedProducts: await listProjectProducts(p.id),
            linking: false,
            selectedProductId: '',
          }))
        )
        setProjects(withProducts)
      })
      .finally(() => setLoading(false))
  }, [orgId])

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orgId || !newProject.trim()) return
    setCreatingProject(true)
    try {
      const p = await createProject(orgId, newProject.trim())
      setProjects(prev => [...prev, { ...p, linkedProducts: [], linking: false, selectedProductId: '' }])
      setNewProject('')
      setShowProjectForm(false)
    } finally {
      setCreatingProject(false)
    }
  }

  const handleCreateProduct = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!orgId || !newProduct.trim()) return
    setCreatingProduct(true)
    try {
      const p = await createProduct(orgId, newProduct.trim())
      setProducts(prev => [...prev, p])
      setNewProduct('')
      setShowProductForm(false)
    } finally {
      setCreatingProduct(false)
    }
  }

  const handleLink = async (project: ProjectWithProducts) => {
    if (!project.selectedProductId) return
    setProjects(prev => prev.map(p => p.id === project.id ? { ...p, linking: true } : p))
    try {
      await linkProductToProject(project.selectedProductId, project.id)
      const linked = products.find(p => p.id === project.selectedProductId)!
      setProjects(prev =>
        prev.map(p =>
          p.id === project.id
            ? { ...p, linkedProducts: [...p.linkedProducts, linked], selectedProductId: '', linking: false }
            : p
        )
      )
    } catch {
      setProjects(prev => prev.map(p => p.id === project.id ? { ...p, linking: false } : p))
    }
  }

  if (loading) return <div className="p-6 text-[#5f6368] text-sm">Loading…</div>
  if (!org) return <div className="p-6 text-[#c5221f] text-sm">Organization not found.</div>

  return (
    <div className="p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link to="/" className="text-sm text-[#1a73e8] hover:underline">← Organizations</Link>
          <h1 className="text-[22px] font-normal text-[#202124] mt-2">{org.name}</h1>
          <div className="mt-1">
            <CopyableId label="org-id" value={org.id} short={false} />
          </div>
        </div>
        <button
          onClick={() => setShowKeyModal(true)}
          className="flex items-center gap-1.5 bg-[#1a73e8] hover:bg-[#1557b0] text-white text-sm font-medium px-4 py-2 rounded transition-colors shadow-sm mt-6"
        >
          <KeyRound size={14} /> Create Key
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ── Projects ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[#202124] flex items-center gap-1.5">
              <FolderOpen size={15} className="text-[#5f6368]" /> Projects
              <span className="ml-1 text-[11px] text-[#9aa0a6] font-normal">({projects.length})</span>
            </h2>
            <button
              onClick={() => setShowProjectForm(v => !v)}
              className="flex items-center gap-1 text-[13px] text-[#1a73e8] hover:bg-[#e8f0fe] px-2 py-1 rounded transition-colors"
            >
              <Plus size={13} /> New
            </button>
          </div>

          {showProjectForm && (
            <form onSubmit={handleCreateProject} className="flex gap-2 mb-3">
              <input
                autoFocus
                value={newProject}
                onChange={e => setNewProject(e.target.value)}
                placeholder="Project name"
                className="flex-1 border border-[#dadce0] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
              />
              <button
                type="submit"
                disabled={creatingProject || !newProject.trim()}
                className="bg-[#1a73e8] hover:bg-[#1557b0] disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 rounded"
              >
                {creatingProject ? '…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowProjectForm(false)}
                className="border border-[#dadce0] text-[#3c4043] text-xs px-3 py-1.5 rounded hover:bg-[#f1f3f4]"
              >
                Cancel
              </button>
            </form>
          )}

          {projects.length === 0 ? (
            <div className="bg-white border border-[#dadce0] rounded-lg p-6 text-center">
              <FolderOpen size={28} className="text-[#dadce0] mx-auto mb-2" />
              <p className="text-sm text-[#5f6368]">No projects yet</p>
            </div>
          ) : (
            <div className="space-y-2">
              {projects.map(p => {
                const unlinked = products.filter(pd => !p.linkedProducts.some(lp => lp.id === pd.id))
                return (
                  <div key={p.id} className="bg-white border border-[#dadce0] rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <Link
                        to={`/projects/${p.id}`}
                        state={{ orgName: org.name, orgId: org.id }}
                        className="flex items-center gap-1.5 text-sm font-medium text-[#1a73e8] hover:underline"
                      >
                        {p.name} <ChevronRight size={13} />
                      </Link>
                      <CopyableId label="project-id" value={p.id} />
                    </div>

                    {/* Linked product chips */}
                    {p.linkedProducts.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2.5">
                        {p.linkedProducts.map(lp => (
                          <span key={lp.id} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#e8f0fe] text-[#1a73e8] rounded-full text-[11px]">
                            <Box size={9} /> {lp.name}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Link dropdown */}
                    {unlinked.length > 0 && (
                      <div className="flex gap-2 pt-1 border-t border-[#f1f3f4] mt-1">
                        <select
                          value={p.selectedProductId}
                          onChange={e =>
                            setProjects(prev =>
                              prev.map(pr => pr.id === p.id ? { ...pr, selectedProductId: e.target.value } : pr)
                            )
                          }
                          className="flex-1 border border-[#dadce0] rounded px-2 py-1 text-xs text-[#3c4043] bg-white focus:outline-none focus:border-[#1a73e8]"
                        >
                          <option value="">Link product…</option>
                          {unlinked.map(pd => (
                            <option key={pd.id} value={pd.id}>{pd.name}</option>
                          ))}
                        </select>
                        <button
                          onClick={() => handleLink(p)}
                          disabled={!p.selectedProductId || p.linking}
                          className="flex items-center gap-1 border border-[#1a73e8] text-[#1a73e8] hover:bg-[#e8f0fe] disabled:opacity-40 text-xs px-3 py-1 rounded transition-colors"
                        >
                          <Link2 size={11} /> {p.linking ? '…' : 'Link'}
                        </button>
                      </div>
                    )}

                    {products.length > 0 && unlinked.length === 0 && (
                      <p className="text-[11px] text-[#34a853] mt-1 flex items-center gap-1">
                        ✓ All products linked
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>

        {/* ── Products ── */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-[#202124] flex items-center gap-1.5">
              <Box size={15} className="text-[#5f6368]" /> Products
              <span className="ml-1 text-[11px] text-[#9aa0a6] font-normal">({products.length})</span>
            </h2>
            <button
              onClick={() => setShowProductForm(v => !v)}
              className="flex items-center gap-1 text-[13px] text-[#1a73e8] hover:bg-[#e8f0fe] px-2 py-1 rounded transition-colors"
            >
              <Plus size={13} /> New
            </button>
          </div>

          {showProductForm && (
            <form onSubmit={handleCreateProduct} className="flex gap-2 mb-3">
              <input
                autoFocus
                value={newProduct}
                onChange={e => setNewProduct(e.target.value)}
                placeholder="Product name"
                className="flex-1 border border-[#dadce0] rounded px-3 py-1.5 text-sm focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
              />
              <button
                type="submit"
                disabled={creatingProduct || !newProduct.trim()}
                className="bg-[#1a73e8] hover:bg-[#1557b0] disabled:opacity-50 text-white text-xs font-medium px-3 py-1.5 rounded"
              >
                {creatingProduct ? '…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowProductForm(false)}
                className="border border-[#dadce0] text-[#3c4043] text-xs px-3 py-1.5 rounded hover:bg-[#f1f3f4]"
              >
                Cancel
              </button>
            </form>
          )}

          {products.length === 0 ? (
            <div className="bg-white border border-[#dadce0] rounded-lg p-6 text-center">
              <Box size={28} className="text-[#dadce0] mx-auto mb-2" />
              <p className="text-sm text-[#5f6368]">No products yet</p>
            </div>
          ) : (
            <div className="bg-white border border-[#dadce0] rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[#f1f3f4]">
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Name</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">ID</th>
                    <th className="px-4 py-2.5 text-left text-xs font-medium text-[#5f6368] uppercase tracking-wider">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(p => (
                    <tr key={p.id} className="border-b border-[#f1f3f4] last:border-0 hover:bg-[#f8f9fa]">
                      <td className="px-4 py-3 text-sm font-medium text-[#202124]">{p.name}</td>
                      <td className="px-4 py-3"><CopyableId label="product-id" value={p.id} /></td>
                      <td className="px-4 py-3 text-xs text-[#5f6368]">
                        {new Date(p.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {showKeyModal && (
        <CreateKeyModal
          orgId={org.id}
          orgName={org.name}
          onCreated={(_result: APIKeyCreated) => setShowKeyModal(false)}
          onClose={() => setShowKeyModal(false)}
        />
      )}
    </div>
  )
}
