import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { startSession } from '@/utils/session'
import Icon from '@/components/ui/Icon'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [remember, setRemember] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void email
    void password
    void remember
    startSession()
    navigate('/inicio')
  }

  return (
    <div className="bg-background min-h-screen flex items-center justify-center relative overflow-hidden font-body-md text-body-md">
      <div className="absolute inset-0 bg-pattern z-0" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary-fixed opacity-40 rounded-full blur-3xl z-0 pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-surface-variant opacity-60 rounded-full blur-3xl z-0 pointer-events-none" />

      <main className="relative z-10 w-full max-w-[420px] px-gutter">
        <div className="bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant p-container-padding flex flex-col gap-8">
          <div className="text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-surface-container-low text-primary rounded-lg border border-outline-variant/30 flex items-center justify-center mb-6 shadow-sm">
              <Icon name="psychology_alt" size="32px" filled />
            </div>
            <h1 className="font-h1-display text-h1-display text-primary tracking-tight">
              BaylonCredit IA
            </h1>
            <p className="font-h3-title text-h3-title text-on-surface-variant mt-1 font-medium">
              Cervecería Baylón
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="email">
                Correo electrónico
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-outline">
                  <Icon name="mail" size="20px" />
                </span>
                <input
                  id="email"
                  type="email"
                  required
                  placeholder="usuario@baylon.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-surface text-on-surface font-body-md text-body-md border border-outline-variant rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-sm"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="password">
                Contraseña
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-outline">
                  <Icon name="lock" size="20px" />
                </span>
                <input
                  id="password"
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-surface text-on-surface font-body-md text-body-md border border-outline-variant rounded-lg pl-10 pr-4 py-2.5 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all shadow-sm"
                />
              </div>
            </div>

            <div className="flex items-center justify-between mt-1">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary focus:ring-2 cursor-pointer"
                />
                <span className="font-body-md text-body-md text-on-surface-variant group-hover:text-on-surface transition-colors">
                  Recordarme
                </span>
              </label>
              <button
                type="button"
                className="font-body-md text-body-md text-primary font-medium hover:text-primary-container hover:underline transition-colors"
              >
                ¿Olvidaste tu contraseña?
              </button>
            </div>

            <button
              type="submit"
              className="w-full mt-2 bg-primary text-on-primary font-body-lg text-body-lg font-semibold py-3 px-4 rounded-lg shadow-sm hover:-translate-y-0.5 hover:shadow-md hover:bg-primary-container transition-all flex items-center justify-center gap-2 active:translate-y-0"
            >
              Iniciar sesión
              <Icon name="arrow_forward" size="20px" />
            </button>
          </form>

          <div className="pt-6 border-t border-surface-variant text-center">
            <p className="font-label-sm text-label-sm text-outline flex items-center justify-center gap-1.5">
              <Icon name="admin_panel_settings" size="16px" />
              Acceso exclusivo para personal autorizado
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
