import { afterEach, describe, expect, test, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import RevisionesCreditoPage from './RevisionesCreditoPage'

interface MockReply {
  status: number
  body: unknown
}

const REVIEWS_URL = '/api/v1/credits/reviews'

const pendingReview = {
  id: 'rev-1',
  client_name: 'Ana Torres',
  requested_amount: 1500,
  score: 640,
  risk: 'medio',
  decision: 'revisar',
  reason: 'Score en el limite',
  status: 'pendiente',
  resolution: null,
  created_at: '2026-11-20T10:00:00Z',
}

let calls: { method: string; path: string }[] = []

function jsonResponse({ status, body }: MockReply) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as unknown as Response
}

function installApi(
  handler: (method: string, url: URL) => MockReply | undefined | Promise<MockReply | undefined>,
) {
  calls = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input))
    const method = (init?.method ?? 'GET').toUpperCase()
    calls.push({ method, path: `${url.pathname}${url.search}` })
    const reply = await handler(method, url)
    if (!reply) throw new Error(`Peticion no simulada: ${method} ${url.pathname}${url.search}`)
    return jsonResponse(reply)
  })
  vi.stubGlobal('fetch', fetchMock)
}

function listOnly() {
  return { status: 200, body: [pendingReview] } satisfies MockReply
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('RevisionesCreditoPage', () => {
  test('lists the pending reviews returned by the queue', async () => {
    installApi(() => listOnly())

    render(<RevisionesCreditoPage />)

    expect(await screen.findByText('Ana Torres')).toBeInTheDocument()
    expect(screen.getByText(/Monto: S\/ 1500\.00/)).toBeInTheDocument()
    expect(screen.getByText(/Score: 640/)).toBeInTheDocument()
    expect(screen.getByText(/Riesgo: medio/)).toBeInTheDocument()
    expect(screen.getByText('Score en el limite')).toBeInTheDocument()
    expect(calls).toEqual([
      { method: 'GET', path: `${REVIEWS_URL}` },
    ])
  })

  test('shows the empty state when there is nothing pending', async () => {
    installApi(() => ({ status: 200, body: [] }))

    render(<RevisionesCreditoPage />)

    expect(await screen.findByText('No hay revisiones pendientes.')).toBeInTheDocument()
  })

  test('assigns a review against the API and reloads the queue', async () => {
    const user = userEvent.setup()
    installApi((method, url) => {
      if (method === 'POST' && url.pathname === `${REVIEWS_URL}/rev-1/assign`) {
        return { status: 200, body: { ...pendingReview, status: 'asignada' } }
      }
      return listOnly()
    })

    render(<RevisionesCreditoPage />)
    await screen.findByText('Ana Torres')

    await user.click(screen.getByRole('button', { name: 'Asignar' }))

    await waitFor(() => {
      expect(calls).toContainEqual({ method: 'POST', path: `${REVIEWS_URL}/rev-1/assign` })
      expect(calls.filter((call) => call.method === 'GET')).toHaveLength(2)
    })
  })

  test('resolves a review with the chosen resolution and reloads the queue', async () => {
    const user = userEvent.setup()
    installApi((method, url) => {
      if (method === 'POST' && url.pathname === `${REVIEWS_URL}/rev-1/resolve`) {
        return { status: 200, body: { ...pendingReview, status: 'resuelta' } }
      }
      return listOnly()
    })

    render(<RevisionesCreditoPage />)
    await screen.findByText('Ana Torres')

    await user.click(screen.getByRole('button', { name: 'Aprobar' }))
    await waitFor(() => {
      expect(calls).toContainEqual({
        method: 'POST',
        path: `${REVIEWS_URL}/rev-1/resolve?resolution=aprobada`,
      })
    })

    await user.click(screen.getByRole('button', { name: 'Rechazar' }))
    await waitFor(() => {
      expect(calls).toContainEqual({
        method: 'POST',
        path: `${REVIEWS_URL}/rev-1/resolve?resolution=rechazada`,
      })
      expect(calls.filter((call) => call.method === 'GET')).toHaveLength(3)
    })
  })

  test('disables the action buttons and ignores a double click while a request is in flight', async () => {
    const user = userEvent.setup()
    let releaseRequest: (() => void) | undefined
    const inFlight = new Promise<void>((resolve) => {
      releaseRequest = resolve
    })
    installApi(async (method) => {
      if (method === 'POST') {
        await inFlight
        return { status: 200, body: { ...pendingReview, status: 'asignada' } }
      }
      return listOnly()
    })

    render(<RevisionesCreditoPage />)
    await screen.findByText('Ana Torres')

    const assign = screen.getByRole('button', { name: 'Asignar' })
    await user.click(assign)

    await waitFor(() => expect(assign).toBeDisabled())
    expect(screen.getByRole('button', { name: 'Aprobar' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Rechazar' })).toBeDisabled()

    fireEvent.click(assign)
    fireEvent.click(screen.getByRole('button', { name: 'Aprobar' }))
    releaseRequest?.()

    await waitFor(() => {
      expect(assign).toBeEnabled()
      expect(calls.filter((call) => call.method === 'GET')).toHaveLength(2)
    })
    expect(calls.filter((call) => call.method === 'POST')).toEqual([
      { method: 'POST', path: `${REVIEWS_URL}/rev-1/assign` },
    ])
  })

  test('surfaces the 403 when the role cannot assign', async () => {
    const user = userEvent.setup()
    installApi((method) =>
      method === 'POST'
        ? { status: 403, body: { detail: 'Sin permiso para asignar revisiones' } }
        : listOnly(),
    )

    render(<RevisionesCreditoPage />)
    await screen.findByText('Ana Torres')

    await user.click(screen.getByRole('button', { name: 'Asignar' }))

    expect(await screen.findByText('Sin permiso para asignar revisiones')).toBeInTheDocument()
    expect(calls.filter((call) => call.method === 'GET')).toHaveLength(1)
  })

  test('surfaces the 403 when the role cannot resolve', async () => {
    const user = userEvent.setup()
    installApi((method) =>
      method === 'POST'
        ? { status: 403, body: { detail: 'Sin permiso para resolver revisiones' } }
        : listOnly(),
    )

    render(<RevisionesCreditoPage />)
    await screen.findByText('Ana Torres')

    await user.click(screen.getByRole('button', { name: 'Aprobar' }))

    expect(await screen.findByText('Sin permiso para resolver revisiones')).toBeInTheDocument()
    expect(screen.getByText('Ana Torres')).toBeInTheDocument()
  })

  test('formats an amount serialized as a decimal string', async () => {
    installApi(() => ({
      status: 200,
      body: [{ ...pendingReview, requested_amount: '1500.00' }],
    }))

    render(<RevisionesCreditoPage />)

    expect(await screen.findByText('Ana Torres')).toBeInTheDocument()
    expect(screen.getByText(/Monto: S\/ 1500\.00/)).toBeInTheDocument()
  })
})
