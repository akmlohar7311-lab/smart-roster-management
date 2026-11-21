
import { useEffect, useMemo, useState } from 'react'
import './RosterPage.css'

const views = [
  { id: 'employee', label: 'Employee-wise' },
  { id: 'brand', label: 'Brand-wise' },
  { id: 'process', label: 'Process-wise' },
  { id: 'pod', label: 'Pod-wise' },
  { id: 'date', label: 'Date-wise' },
]

const PAGE_SIZE = 50

function uniqueValues(entries, key) {
  return [...new Set(entries.map(item => item[key]))]
    .filter(Boolean)
    .sort()
}

function formatTime(value) {
  if (!value) return '-'
  return String(value).slice(0, 5)
}

function RosterPage() {
  const [month, setMonth] = useState('2026-12')
  const [roster, setRoster] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [view, setView] = useState('employee')
  const [employee, setEmployee] = useState('')
  const [brand, setBrand] = useState('')
  const [process, setProcess] = useState('')
  const [pod, setPod] = useState('')
  const [date, setDate] = useState('')
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  async function loadRoster() {
    setLoading(true)
    setError('')
    setRoster(null)

    try {
      const [year, monthNumber] = month.split('-')

      const response = await fetch(
        `/api/roster-view/monthly?year=${year}&month=${Number(monthNumber)}`
      )

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('No saved roster found for this month.')
        }

        throw new Error(`Unable to load roster (HTTP ${response.status})`)
      }

      const data = await response.json()
      setRoster(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRoster()
  }, [month])

  const entries = roster?.entries || []

  const filtered = useMemo(() => {
    const query = search.toLowerCase().trim()

    return entries.filter(item => {
      if (employee && item.employee_code !== employee) return false
      if (brand && item.brand !== brand) return false
      if (process && item.process !== process) return false
      if (pod && item.pod !== pod) return false
      if (date && item.work_date !== date) return false
      if (status && item.status !== status) return false

      if (query) {
        const text = [
          item.employee_name,
          item.employee_code,
          item.brand,
          item.process,
          item.pod,
          item.work_date
        ].join(' ').toLowerCase()

        if (!text.includes(query)) return false
      }

      return true
    })
  }, [entries, employee, brand, process, pod, date, status, search])

  const groupField = {
    employee: 'employee_name',
    brand: 'brand',
    process: 'process',
    pod: 'pod',
    date: 'work_date'
  }[view]

  const groups = useMemo(() => {
    const counts = {}

    filtered.forEach(item => {
      const key = item[groupField] || 'Unknown'
      counts[key] = (counts[key] || 0) + 1
    })

    return Object.entries(counts).sort(
      (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
    )
  }, [filtered, groupField])

  const totalPages = Math.max(
    1,
    Math.ceil(filtered.length / PAGE_SIZE)
  )

  const visible = filtered.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  )

  function resetPage(setter) {
    return value => {
      setter(value)
      setPage(1)
    }
  }

  function clearFilters() {
    setEmployee('')
    setBrand('')
    setProcess('')
    setPod('')
    setDate('')
    setStatus('')
    setSearch('')
    setPage(1)
  }

  return (
    <div className="roster-page">
      <section className="roster-toolbar">
        <div>
          <h2>Monthly Employee Roster</h2>
          <p>Live schedules from your Supabase database</p>
        </div>

        <div className="roster-toolbar-actions">
          <label htmlFor="roster-month">Roster month</label>
          <input
            id="roster-month"
            type="month"
            value={month}
            onChange={e => {
              setMonth(e.target.value)
              clearFilters()
            }}
          />
          <button onClick={loadRoster} disabled={loading}>
            Refresh
          </button>
        </div>
      </section>

      {loading && (
        <div className="roster-message">Loading monthly roster...</div>
      )}

      {error && (
        <div className="roster-message error" role="alert">
          {error}
        </div>
      )}

      {roster && !loading && (
        <>
          <div className="roster-stats">
            <div>
              <span>Roster version</span>
              <strong>V{roster.version}</strong>
            </div>
            <div>
              <span>Working shifts</span>
              <strong>{roster.working_shifts}</strong>
            </div>
            <div>
              <span>Cancelled shifts</span>
              <strong>{roster.cancelled_shifts}</strong>
            </div>
            <div>
              <span>Roster status</span>
              <strong>{roster.status}</strong>
            </div>
          </div>

          <section className="roster-panel">
            <div className="roster-section-title">
              <h3>Roster Views</h3>
              <p>Select how you want to explore the roster.</p>
            </div>

            <div className="roster-view-tabs">
              {views.map(item => (
                <button
                  key={item.id}
                  className={view === item.id ? 'chosen' : ''}
                  onClick={() => {
                    setView(item.id)
                    setPage(1)
                  }}
                >
                  {item.label}
                </button>
              ))}
            </div>

            <div className="roster-filters">
              <label>
                Employee
                <select
                  value={employee}
                  onChange={e => resetPage(setEmployee)(e.target.value)}
                >
                  <option value="">All employees</option>
                  {uniqueValues(entries, 'employee_code').map(code => (
                    <option key={code} value={code}>{code}</option>
                  ))}
                </select>
              </label>

              <label>
                Brand
                <select
                  value={brand}
                  onChange={e => resetPage(setBrand)(e.target.value)}
                >
                  <option value="">All brands</option>
                  {uniqueValues(entries, 'brand').map(value => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </label>

              <label>
                Process
                <select
                  value={process}
                  onChange={e => resetPage(setProcess)(e.target.value)}
                >
                  <option value="">All processes</option>
                  {uniqueValues(entries, 'process').map(value => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </label>

              <label>
                Pod
                <select
                  value={pod}
                  onChange={e => resetPage(setPod)(e.target.value)}
                >
                  <option value="">All pods</option>
                  {uniqueValues(entries, 'pod').map(value => (
                    <option key={value} value={value}>{value}</option>
                  ))}
                </select>
              </label>

              <label>
                Date
                <input
                  type="date"
                  min={`${month}-01`}
                  max={`${month}-31`}
                  value={date}
                  onChange={e => resetPage(setDate)(e.target.value)}
                />
              </label>

              <label>
                Status
                <select
                  value={status}
                  onChange={e => resetPage(setStatus)(e.target.value)}
                >
                  <option value="">All statuses</option>
                  <option value="working">Working</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
            </div>

            <div className="roster-search-row">
              <input
                type="search"
                placeholder="Search employee, brand, process or date..."
                value={search}
                onChange={e => resetPage(setSearch)(e.target.value)}
              />
              <button onClick={clearFilters}>Clear Filters</button>
            </div>
          </section>

          <section className="roster-panel">
            <div className="roster-section-title">
              <h3>{views.find(item => item.id === view)?.label} Summary</h3>
              <p>{filtered.length} shifts match the selected filters.</p>
            </div>

            <div className="roster-group-list">
              {groups.slice(0, 20).map(([name, count]) => (
                <div className="roster-group" key={name}>
                  <span>{name}</span>
                  <strong>{count} shifts</strong>
                </div>
              ))}
              {groups.length > 20 && (
                <p className="roster-muted">
                  Showing the first 20 groups of {groups.length}.
                </p>
              )}
              {groups.length === 0 && (
                <p className="roster-muted">No matching shifts.</p>
              )}
            </div>
          </section>

          <section className="roster-panel">
            <div className="roster-section-title">
              <h3>Shift Details</h3>
              <p>
                Showing {visible.length} of {filtered.length} matching entries
              </p>
            </div>

            <div className="roster-table-scroll">
              <table className="roster-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Employee</th>
                    <th>Brand</th>
                    <th>Process</th>
                    <th>Pod</th>
                    <th>Time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map(item => (
                    <tr key={item.entry_id}>
                      <td>{item.work_date}</td>
                      <td>
                        <strong>{item.employee_name}</strong>
                        <small>{item.employee_code}</small>
                      </td>
                      <td>{item.brand}</td>
                      <td>{item.process_code || item.process}</td>
                      <td>{item.pod}</td>
                      <td>
                        {formatTime(item.start_time)}
                        {' – '}
                        {formatTime(item.end_time)}
                      </td>
                      <td>
                        <span className={
                          item.status === 'working'
                            ? 'roster-status working'
                            : 'roster-status cancelled'
                        }>
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filtered.length === 0 && (
              <div className="roster-message">
                No shifts match these filters.
              </div>
            )}

            <div className="roster-pagination">
              <span>Page {page} of {totalPages}</span>

              <div>
                <button
                  disabled={page === 1}
                  onClick={() => setPage(p => p - 1)}
                >
                  Previous
                </button>

                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage(p => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

export default RosterPage
