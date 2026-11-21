
import { apiFetch } from './lib/api'

import RosterEditorPage from './RosterEditorPage'
import AICopilotPage from './AICopilotPage'
import ConflictsPage from './ConflictsPage'
import LeavesPage from './LeavesPage'
import RosterPage from './RosterPage'
import AssignmentsPage from './AssignmentsPage'

import { useEffect, useMemo, useState } from 'react'
import './App.css'

const navigation = [
  { id: 'dashboard', icon: '▦', label: 'Dashboard' },
  { id: 'employees', icon: '♙', label: 'Employees' },
  { id: 'assignments', icon: '⇄', label: 'Assignments' },
  { id: 'roster', icon: '▤', label: 'Monthly Roster' },
  { id: 'leaves', icon: '▣', label: 'Leave Management' },
  { id: 'conflicts', icon: '⚠', label: 'Conflicts' },
  { id: 'editor', icon: '✎', label: 'Roster Editor' },
  { id: 'ai-copilot', icon: '✦', label: 'AI Copilot' },
]

const quickLinks = [
  ['roster', '\u25A4', 'Monthly Roster'],
  ['leaves', '\u25A3', 'Leave Management'],
  ['conflicts', '\u26A0', 'View Conflicts'],
  ['editor', '\u270E', 'Roster Editor'],
  ['assignments', '\u21C4', 'Assignments'],
  ['ai-copilot', '\u2726', 'AI Copilot'],
]

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [employees, setEmployees] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  async function loadEmployees() {
    setLoading(true)
    setError('')

    try {
      const response = await apiFetch('/api/employees')

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = await response.json()

      setEmployees(data.employees || [])

    } catch (err) {
      setError(
        'Could not load employees. Check that FastAPI is running and the Vite proxy is configured correctly.'
      )

      console.error('Employee API error:', err)

    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadEmployees()
  }, [])

  const activeEmployees = employees.filter(e => e.active)
  const inactiveEmployees = employees.filter(e => !e.active)

  const filteredEmployees = useMemo(() => {
    const term = search.toLowerCase().trim()

    return employees.filter(employee =>
      employee.name.toLowerCase().includes(term) ||
      employee.employee_code.toLowerCase().includes(term) ||
      employee.email.toLowerCase().includes(term)
    )
  }, [employees, search])

  const currentPage = navigation.find(
    item => item.id === activePage
  )

  function navigate(page) {
    setActivePage(page)
    setSidebarOpen(false)
  }

  function EmployeeTable({ rows }) {
    return (
      <div className="table-scroll">

        <table className="employee-table">

          <thead>
            <tr>
              <th>Employee</th>
              <th>Employee ID</th>
              <th>Email</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>

            {rows.map(employee => (
              <tr key={employee.employee_code}>

                <td>
                  <div className="employee-identity">

                    <div className="avatar">
                      {employee.name
                        .split(' ')
                        .slice(0, 2)
                        .map(part => part[0])
                        .join('')
                        .toUpperCase()}
                    </div>

                    <strong>{employee.name}</strong>

                  </div>
                </td>

                <td>
                  <span className="employee-code">
                    {employee.employee_code}
                  </span>
                </td>

                <td>{employee.email}</td>

                <td>
                  <span className={
                    employee.active
                      ? 'status active'
                      : 'status inactive'
                  }>
                    {employee.active ? 'Active' : 'Inactive'}
                  </span>
                </td>

              </tr>
            ))}

          </tbody>

        </table>

        {rows.length === 0 && (
          <div className="empty-state">
            No matching employees found.
          </div>
        )}

      </div>
    )
  }

  function PagePlaceholder() {
    const descriptions = {
      roster: 'Monthly schedule, calendar and brand/process filters.',
      leaves: 'Leave requests, approvals and automatic revalidation.',
      conflicts: 'Coverage shortages, leave violations and warnings.',
      editor: 'Cancel, reassign and fill shifts with eligible employees.'
    }

    return (
      <section className="panel placeholder-panel">

        <div className="placeholder-icon">
          {currentPage?.icon}
        </div>

        <h2>{currentPage?.label}</h2>

        <p>{descriptions[activePage]}</p>

        <span className="coming-soon">
          This section is next in our build.
        </span>

      </section>
    )
  }

  return (
    <div className="app-shell">

      {/* Mobile Sidebar Overlay */}

      {sidebarOpen && (
        <button
          className="mobile-overlay"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>

        <div className="brand">

          <div className="brand-logo">D</div>

          <div>
            <h2>Datastraw</h2>
            <span>Smart Roster System</span>
          </div>

        </div>

        <div className="sidebar-section-label">
          WORKSPACE
        </div>

        <nav
          className="sidebar-nav"
          aria-label="Main navigation"
        >

          {navigation.map(item => (
            <button
              key={item.id}
              type="button"
              className={
                activePage === item.id
                  ? 'nav-item selected'
                  : 'nav-item'
              }
              onClick={() => navigate(item.id)}
            >

              <span className="nav-icon">
                {item.icon}
              </span>

              <span>{item.label}</span>

            </button>
          ))}

        </nav>

        <div className="sidebar-footer">

          <div className="connection-dot" />

          <div>
            <strong>Local development</strong>
            <small>React + FastAPI + Supabase</small>
          </div>

        </div>

      </aside>

      {/* Main Area */}

      <div className="main-area">

        {/* Top Navigation */}

        <header className="topbar">

          <div className="topbar-left">

            <button
              className="menu-button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              {'\u2630'}
            </button>

            <span className="breadcrumb">
              Workspace / {currentPage?.label}
            </span>

          </div>

          <div className="topbar-right">

            <span className="environment-tag">
              Development
            </span>

            <div className="profile-avatar">
              M
            </div>

          </div>

        </header>

        {/* Page Content */}

        <main className="page-content">

          <div className="page-heading">

            <div>

              <p className="eyebrow">
                WORKFORCE MANAGEMENT
              </p>

              <h1>
                {activePage === 'dashboard'
                  ? 'Dashboard Overview'
                  : currentPage?.label}
              </h1>

              <p className="page-subtitle">
                {activePage === 'dashboard'
                  ? 'Manage your team and monitor workforce data.'
                  : activePage === 'employees'
                  ? 'Browse and search your employee records.'
                  : activePage === 'ai-copilot'
                  ? 'Ask Gemini for workforce planning and scheduling guidance.'
                  : 'Datastraw Smart Roster Management System'}
              </p>

            </div>

            {activePage !== 'ai-copilot' && (
              <button
                className="refresh-button"
                onClick={loadEmployees}
                disabled={loading}
              >
                {'\u21BB'} Refresh Data
              </button>
            )}

          </div>

          {/* Error Message */}

          {error && (
            <div className="error-banner" role="alert">
              {error}
            </div>
          )}

          {/* Dashboard */}

          {activePage === 'dashboard' && (
            <>

              {/* Statistics Cards */}

              <div className="stats-grid">

                <div className="stat-card">

                  <div className="stat-top">

                    <span>Total Employees</span>

                    <div className="stat-icon blue">
                      {'\u{1F465}'}
                    </div>

                  </div>

                  <h2>
                    {loading ? '...' : employees.length}
                  </h2>

                  <p>Registered workforce</p>

                </div>

                <div className="stat-card">

                  <div className="stat-top">

                    <span>Active Employees</span>

                    <div className="stat-icon green">
                      {'\u2713'}
                    </div>

                  </div>

                  <h2>
                    {loading ? '...' : activeEmployees.length}
                  </h2>

                  <p>Currently marked active</p>

                </div>

                <div className="stat-card">

                  <div className="stat-top">

                    <span>Inactive Employees</span>

                    <div className="stat-icon amber">
                      {'\u25CB'}
                    </div>

                  </div>

                  <h2>
                    {loading ? '...' : inactiveEmployees.length}
                  </h2>

                  <p>Currently marked inactive</p>

                </div>

                <div className="stat-card">

                  <div className="stat-top">

                    <span>Backend</span>

                    <div className="stat-icon purple">
                      {'\u26A1'}
                    </div>

                  </div>

                  <h2 className="stat-status">
                    {loading
                      ? 'Checking'
                      : error
                      ? 'Offline'
                      : 'Connected'}
                  </h2>

                  <p>FastAPI employee endpoint</p>

                </div>

              </div>

              {/* Dashboard Grid */}

              <div className="dashboard-grid">

                {/* Employee Directory */}

                <section className="panel">

                  <div className="panel-heading">

                    <div>
                      <h2>Employee Directory</h2>
                      <p>Live records from Supabase</p>
                    </div>

                    <button
                      className="text-button"
                      onClick={() => navigate('employees')}
                    >
                      View All {'\u2192'}
                    </button>

                  </div>

                  {loading
                    ? (
                      <div className="empty-state">
                        Loading employees...
                      </div>
                    )
                    : (
                      <EmployeeTable
                        rows={employees.slice(0, 6)}
                      />
                    )
                  }

                </section>

                {/* Quick Access */}

                <section className="panel quick-panel">

                  <div className="panel-heading">

                    <div>
                      <h2>Quick Access</h2>
                      <p>Explore roster management</p>
                    </div>

                  </div>

                  {quickLinks.map(([id, icon, label]) => (

                    <button
                      key={id}
                      className="quick-link"
                      onClick={() => navigate(id)}
                    >

                      <span>{icon}</span>

                      <strong>{label}</strong>

                      <span className="quick-arrow">
                        {'\u2192'}
                      </span>

                    </button>

                  ))}

                  <div className="quick-note">
                    Explore workforce tools and ask AI Copilot
                    for scheduling guidance.
                  </div>

                </section>

              </div>

            </>
          )}

          {/* Employees Page */}

          {activePage === 'employees' && (

            <section className="panel">

              <div className="panel-heading employees-heading">

                <div>
                  <h2>All Employees</h2>

                  <p>
                    {filteredEmployees.length} employee records
                  </p>
                </div>

                <input
                  className="search-input"
                  type="search"
                  placeholder="Search name, ID or email..."
                  value={search}
                  onChange={event => setSearch(event.target.value)}
                />

              </div>

              {loading
                ? (
                  <div className="empty-state">
                    Loading employees...
                  </div>
                )
                : (
                  <EmployeeTable rows={filteredEmployees} />
                )
              }

            </section>

          )}

          {/* Other Application Pages */}

          {activePage === 'assignments' && (
            <AssignmentsPage />
          )}

          {activePage === 'roster' && (
            <RosterPage />
          )}

          {activePage === 'conflicts' && (
            <ConflictsPage />
          )}

          {activePage === 'leaves' && (
            <LeavesPage />
          )}

          {activePage === 'editor' && (
            <RosterEditorPage />
          )}

          {activePage === 'ai-copilot' && (
            <AICopilotPage />
          )}

          {/* Footer */}

          <footer className="footer">
            Datastraw Smart Roster Management System

            <span>
              Local development dashboard
            </span>
          </footer>

        </main>

      </div>

    </div>
  )
}

export default App
