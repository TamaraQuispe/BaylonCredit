import { useEffect, useState } from 'react'
import { apiRequest } from '@/services/apiClient'

interface Review {
  id: string
  client_name: string | null
  requested_amount: number | string
  score: number
  risk: string
  decision: string
  reason: string | null
  status: string
  resolution: string | null
  created_at: string
}

export default function RevisionesCreditoPage() {
  const [items, setItems] = useState<Review[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await apiRequest<Review[]>('/credits/reviews?status=pendiente')
      setItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo cargar la cola')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function assign(id: string) {
    setError(null)
    setBusy(true)
    try {
      await apiRequest(`/credits/reviews/${id}/assign`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo asignar')
    } finally {
      setBusy(false)
    }
  }

  async function resolve(id: string, resolution: 'aprobada' | 'rechazada') {
    setError(null)
    setBusy(true)
    try {
      await apiRequest(`/credits/reviews/${id}/resolve?resolution=${resolution}`, { method: 'POST' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo resolver')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Revisiones de credito pendientes</h1>
      {loading && <p>Cargando...</p>}
      {error && <p className="text-red-600">{error}</p>}
      {!loading && items.length === 0 && <p>No hay revisiones pendientes.</p>}
      <ul className="space-y-3">
        {items.map((item) => (
          <li key={item.id} className="border rounded p-3 space-y-2">
            <div className="flex justify-between">
              <span className="font-medium">{item.client_name || 'Cliente'}</span>
              <span className="text-sm text-gray-500">{item.status}</span>
            </div>
            <div className="text-sm">
              Monto: S/ {Number(item.requested_amount).toFixed(2)} · Score: {item.score} · Riesgo: {item.risk}
            </div>
            {item.reason && <div className="text-sm text-gray-600">{item.reason}</div>}
            <div className="flex gap-2">
              <button
                className="px-3 py-1 bg-blue-600 text-white rounded disabled:opacity-50"
                disabled={busy}
                onClick={() => void assign(item.id)}
              >
                Asignar
              </button>
              <button
                className="px-3 py-1 bg-green-600 text-white rounded disabled:opacity-50"
                disabled={busy}
                onClick={() => void resolve(item.id, 'aprobada')}
              >
                Aprobar
              </button>
              <button
                className="px-3 py-1 bg-red-600 text-white rounded disabled:opacity-50"
                disabled={busy}
                onClick={() => void resolve(item.id, 'rechazada')}
              >
                Rechazar
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}