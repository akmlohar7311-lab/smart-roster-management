import { apiFetch } from './lib/api'

import { useEffect, useState } from 'react'
import './ManagementPages.css'

export default function ConflictsPage() {
  const [month, setMonth] = useState('2026-12')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [dateFilter, setDateFilter] = useState('')

  async function loadConflicts() {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const [year, monthNumber] = month.split('-')

      // First find the saved roster for this month.
      const rosterResponse = await apiFetch(
        `/api/roster-view/monthly?year=${year}&month=${Number(monthNumber)}`
      )

      if (!rosterResponse.ok) {
        throw new Error(
          rosterResponse.status === 404
            ? 'No saved roster exists for this month.'
            : 'Could not load the roster.'
        )
      }

      const roster = await rosterResponse.json()

      // Then independently validate that roster.
      const response = await apiFetch(
        `/api/rosters/${roster.roster_id}/validate`
      )

      if (!response.ok) {
        throw new Error('Roster validation request failed.')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConflicts()
  }, [month])

  const violations = result?.violations || []
  const summary = result?.violation_summary || {}

  const types = [...new Set(
    violations.map(item => item.type)
  )].sort()

  const filtered = violations.filter(item => {
    if (typeFilter !== 'all' && item.type !== typeFilter) {
      return false
    }

    if (dateFilter && item.date !== dateFilter) {
      return false
    }

    return true
  })

  function prettyType(type) {
    return type.replaceAll('_', ' ')
  }

  return (
    <div className="management-page">
      <section className="management-panel">
        <div className="management-header">
          <div>
            <h2>Roster Conflict Monitor</h2>
            <p>
              Live validation against current leave,
              assignment and scheduling rules.
            </p>
          </div>

          <div className="management-actions">
            <input
              aria-label="Roster month"
              type="month"
              value={month}
              onChange={e => {
                setMonth(e.target.value)
                setTypeFilter('all')
                setDateFilter('')
              }}
            />
            <button
              onClick={loadConflicts}
              disabled={loading}
            >
              {loading ? 'Checking...' : 'Revalidate'}
            </button>
          </div>
        </div>

        {error && (
          <div className="management-error" role="alert">
            {error}
          </div>
        )}

        {result && (
          <>
            <div className="management-stats">
              <div>
                <span>Roster Version</span>
                <strong>V{result.version}</strong>
              </div>
              <div>
                <span>Saved Entries</span>
                <strong>{result.total_shifts}</strong>
              </div>
              <div>
                <span>Violations</span>
                <strong className="danger-text">
                  {result.total_violations}
                </strong>
              </div>
              <div>
                <span>Leave Violations</span>
                <strong>{summary.leave_violation || 0}</strong>
              </div>
              <div>
                <span>Coverage Shortages</span>
                <strong>{summary.insufficient_coverage || 0}</strong>
              </div>
            </div>

            <h3>Violations by Type</h3>

            <div className="management-summary">
              {Object.entries(summary).map(([type, count]) => (
                <div className="summary-chip" key={type}>
                  <span>{prettyType(type)}</span>
                  <strong>{count}</strong>
                </div>
              ))}

              {Object.keys(summary).length === 0 && (
                <p>No violations found.</p>
              )}
            </div>

            <div className="management-filters">
              <label>
                Conflict type
                <select
                  value={typeFilter}
                  onChange={e => setTypeFilter(e.target.value)}
                >
                  <option value="all">All types</option>
                  {types.map(type => (
                    <option key={type} value={type}>
                      {prettyType(type)}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Date
                <input
                  type="date"
                  value={dateFilter}
                  onChange={e => setDateFilter(e.target.value)}
                />
              </label>

              <button
                className="secondary-button"
                onClick={() => {
                  setTypeFilter('all')
                  setDateFilter('')
                }}
              >
                Clear Filters
              </button>
            </div>

            <p className="management-count">
              Showing {filtered.length} violations
            </p>

            <div className="management-table-scroll">
              <table className="management-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Employee / Brand</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item, index) => (
                    <tr key={`${item.type}-${item.date}-${index}`}>
                      <td>{item.date}</td>
                      <td>
                        <span className="management-tag error-tag">
                          {prettyType(item.type)}
                        </span>
                      </td>
                      <td>
                        {item.employee || item.brand || '-'}
                      </td>
                      <td>{item.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filtered.length === 0 && (
              <p className="management-empty">
                No violations match the current filters.
              </p>
            )}
          </>
        )}
      </section>
    </div>
  )
}

