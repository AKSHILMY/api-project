import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import OrgDetail from './pages/OrgDetail'
import ProjectDetail from './pages/ProjectDetail'
import VerifyKey from './pages/VerifyKey'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="/orgs/:orgId" element={<OrgDetail />} />
          <Route path="/projects/:projectId" element={<ProjectDetail />} />
          <Route path="/verify" element={<VerifyKey />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
