import { useEffect, useState } from "react"
import { api, Camera, ComplianceEvent, CountSummary } from "./api"

type Tab = "overview" | "events" | "counts" | "cameras" | "reports"

const tabs: Tab[] = ["overview", "events", "counts", "cameras", "reports"]

export default function App() {
  const [tab, setTab] = useState<Tab>("overview")
  const [cameras, setCameras] = useState<Camera[]>([])
  const [events, setEvents] = useState<ComplianceEvent[]>([])
  const [counts, setCounts] = useState<CountSummary[]>([])
  const [ready, setReady] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([api.ready(), api.cameras(), api.events(), api.counts()])
      .then(([health, cameraPage, eventPage, countRows]) => {
        setReady(health.status === "ready")
        setCameras(cameraPage.items)
        setEvents(eventPage.items)
        setCounts(countRows)
      })
      .catch((reason: Error) => setError(reason.message))
  }, [])

  return (
    <div className="app">
      <header>
        <h1>Kitchen Vision</h1>
        <span className={`status ${ready ? "ok" : "bad"}`}>
          {ready ? "API ready" : "API unavailable"}
        </span>
      </header>
      {!ready && <div className="banner">Camera or inference health is not current. Missing data is not zero violations.</div>}
      {error && <div className="banner">{error}</div>}
      <nav>
        {tabs.map((item) => (
          <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>
            {item}
          </button>
        ))}
      </nav>
      <main>
        {tab === "overview" && <Overview cameras={cameras} events={events} counts={counts} />}
        {tab === "events" && <Events events={events} />}
        {tab === "counts" && <Counts counts={counts} />}
        {tab === "cameras" && <Cameras cameras={cameras} />}
        {tab === "reports" && <Reports />}
      </main>
    </div>
  )
}

function Overview({ cameras, events, counts }: { cameras: Camera[]; events: ComplianceEvent[]; counts: CountSummary[] }) {
  const violations = events.filter((event) => event.status === "violation").length
  const unclear = events.filter((event) => event.status === "unclear").length
  const totalCount = counts.reduce((sum, row) => sum + row.count, 0)
  return (
    <section>
      <h2>Overview</h2>
      <div className="cards">
        <Card label="Cameras" value={cameras.length} />
        <Card label="Violation events" value={violations} />
        <Card label="Unclear events" value={unclear} />
        <Card label="Counted utensils" value={totalCount} />
      </div>
    </section>
  )
}

function Card({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function Events({ events }: { events: ComplianceEvent[] }) {
  return (
    <section>
      <h2>Events</h2>
      <table>
        <thead>
          <tr><th>Time</th><th>Camera</th><th>Item</th><th>Status</th><th>Review</th></tr>
        </thead>
        <tbody>
          {events.map((event) => (
            <tr key={event.id}>
              <td>{new Date(event.occurred_at).toLocaleString()}</td>
              <td>{event.camera_id}</td>
              <td>{event.item}</td>
              <td>{event.status}</td>
              <td>{event.review_state}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function Counts({ counts }: { counts: CountSummary[] }) {
  return (
    <section>
      <h2>Counts</h2>
      <table>
        <thead>
          <tr><th>Bucket</th><th>Camera</th><th>Class</th><th>Mode</th><th>Count</th></tr>
        </thead>
        <tbody>
          {counts.map((row, index) => (
            <tr key={`${row.camera_id}-${row.class_name}-${index}`}>
              <td>{new Date(row.bucket_start).toLocaleString()}</td>
              <td>{row.camera_id}</td>
              <td>{row.class_name}</td>
              <td>{row.mode}</td>
              <td>{row.count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function Cameras({ cameras }: { cameras: Camera[] }) {
  return (
    <section>
      <h2>Cameras</h2>
      <table>
        <thead>
          <tr><th>ID</th><th>Name</th><th>Active</th><th>Resolution</th><th>FPS</th></tr>
        </thead>
        <tbody>
          {cameras.map((camera) => (
            <tr key={camera.id}>
              <td>{camera.id}</td>
              <td>{camera.name}</td>
              <td>{camera.active ? "yes" : "no"}</td>
              <td>{camera.resolution ?? "-"}</td>
              <td>{camera.fps ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function Reports() {
  return (
    <section>
      <h2>Reports</h2>
      <p>CSV export is available from /api/v1/exports/events.csv and /api/v1/exports/counts.csv.</p>
      <p>Email scheduling is available through /api/v1/report-schedules.</p>
    </section>
  )
}
