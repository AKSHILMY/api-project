import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export interface Organization {
  id: string
  name: string
  created_at: string
}

export interface Project {
  id: string
  name: string
  org_id: string
  created_at: string
}

export interface Product {
  id: string
  name: string
  org_id: string
  created_at: string
}

export interface KeyMetadata {
  name: string | null
  scopes: string[]
  rate_limit: number | null
  expires_at: string | null
  custom: Record<string, unknown>
}

export interface APIKey {
  id: string
  org_id: string
  project_id: string | null
  product_id: string | null
  key_prefix: string
  metadata: KeyMetadata
  revoked_at: string | null
  created_at: string
}

export interface APIKeyCreated {
  key: APIKey
  plaintext: string
}

export interface CreateKeyBody {
  org_id: string
  project_id?: string
  product_id?: string
  name?: string
  scopes?: string[]
  rate_limit?: number
  expires_at?: string
  custom?: Record<string, unknown>
}

// Orgs
export const listOrgs = () => http.get<Organization[]>('/orgs').then(r => r.data)
export const createOrg = (name: string) => http.post<Organization>('/orgs', { name }).then(r => r.data)
export const getOrg = (id: string) => http.get<Organization>(`/orgs/${id}`).then(r => r.data)

// Projects
export const listProjects = (orgId: string) => http.get<Project[]>(`/orgs/${orgId}/projects`).then(r => r.data)
export const createProject = (orgId: string, name: string) =>
  http.post<Project>(`/orgs/${orgId}/projects`, { name }).then(r => r.data)

// Products
export const listProducts = (orgId: string) => http.get<Product[]>(`/orgs/${orgId}/products`).then(r => r.data)
export const createProduct = (orgId: string, name: string) =>
  http.post<Product>(`/orgs/${orgId}/products`, { name }).then(r => r.data)
export const linkProductToProject = (productId: string, projectId: string) =>
  http.post(`/products/${productId}/projects/${projectId}`)
export const listProjectProducts = (projectId: string) =>
  http.get<Product[]>(`/projects/${projectId}/products`).then(r => r.data)

// Keys
export const listOrgKeys = (orgId: string) => http.get<APIKey[]>(`/orgs/${orgId}/keys`).then(r => r.data)
export const listKeys = (projectId: string) => http.get<APIKey[]>(`/projects/${projectId}/keys`).then(r => r.data)
export const createKey = (body: CreateKeyBody) =>
  http.post<APIKeyCreated>('/keys', body).then(r => r.data)
export const revokeKey = (keyId: string) => http.delete<APIKey>(`/keys/${keyId}`).then(r => r.data)
export const verifyKey = (key: string) => http.post<APIKey>('/keys/verify', { key }).then(r => r.data)
