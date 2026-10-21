import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import ManagerApp from './manager/ManagerApp'
import Ask from './pages/Ask'
import Compare from './pages/Compare'
import Connections from './pages/Connections'
import Dashboard from './pages/Dashboard'
import Data from './pages/Data'
import Run from './pages/Run'
import Runs from './pages/Runs'

const router = createBrowserRouter([
  // The manager-facing chat is the main screen; the technical console lives under /console.
  { path: '/', element: <ManagerApp /> },
  {
    path: '/console',
    element: <Layout />,
    children: [
      { index: true, element: <Ask /> },
      { path: 'runs', element: <Runs /> },
      { path: 'runs/:id', element: <Run /> },
      { path: 'compare', element: <Compare /> },
      { path: 'dashboard', element: <Dashboard /> },
      { path: 'data', element: <Data /> },
      { path: 'connections', element: <Connections /> },
    ],
  },
  // Old addresses from before the technical pages moved under /console, and anything unknown.
  { path: '/runs/:id', element: <OldRunRedirect /> },
  ...['runs', 'compare', 'dashboard', 'data', 'connections'].map((page) => ({ path: `/${page}`, element: <Navigate to={`/console/${page}`} replace /> })),
  { path: '*', element: <Navigate to="/" replace /> },
])

function OldRunRedirect() {
  const { id } = useParams()
  return <Navigate to={`/console/runs/${id}`} replace />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
