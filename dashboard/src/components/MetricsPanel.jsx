import React, { useEffect, useState } from 'react'
import { fetchMetricsSummary } from '../api.js'

export default function MetricsPanel() {
  const [metrics, setMetrics] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    fetchMetricsSummary()
      .then((data) => {
        if (active) {
          setMetrics(data)
          setLoading(false)
        }
      })
      .catch(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  if (loading || !metrics) return null

  return (
    <div className="metrics-panel">
      <div className="metric-card">
        <div className="metric-label">Total QA Runs</div>
        <div className="metric-value">{metrics.total_runs}</div>
      </div>
      <div className="metric-card">
        <div className="metric-label">Fix Success Rate</div>
        <div className="metric-value text-success">{metrics.success_rate_percentage}%</div>
      </div>
      <div className="metric-card">
        <div className="metric-label">Needs Review</div>
        <div className="metric-value text-warning">{metrics.needs_review_runs}</div>
      </div>
      <div className="metric-card">
        <div className="metric-label">Avg Pixel Diff Reduction</div>
        <div className="metric-value">{(metrics.average_diff_reduction * 100).toFixed(2)}%</div>
      </div>
    </div>
  )
}
