import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, test, vi } from 'vitest'

const state = vi.hoisted(() => ({ rol: 'operator' as 'operator' | 'viewer' | 'admin' }))

vi.mock('@/utils/session', () => ({
  getSession: () => ({ rol: state.rol }),
  endSession: vi.fn(),
}))

vi.mock('@/services/apiClient', () => ({
  logout: vi.fn(),
}))

import Sidebar from './Sidebar'

describe('Sidebar', () => {
  test('links the credit review queue for operators', () => {
    state.rol = 'operator'

    render(
      <MemoryRouter>
        <Sidebar open onClose={() => {}} />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /Revisiones/ })
    expect(link).toHaveAttribute('href', '/revisiones-credito')
  })
})
