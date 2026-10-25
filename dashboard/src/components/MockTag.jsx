import { DATA_SOURCE } from '../api.js'

// Shown next to every run id while on fixtures, so a screenshot of one row still says "mock".
export default function MockTag() {
  return DATA_SOURCE === 'mock' ? <span className="mock-tag" data-testid="mock-tag">Mock</span> : null
}
