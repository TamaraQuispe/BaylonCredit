import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { completeRegistration } from '@/services/apiClient'
import { endSession } from '@/utils/session'

export default function CambiarContrasenaInicialPage() {
  const navigate = useNavigate()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (newPassword.length < 10) {
      setError('La contraseña debe tener al menos 10 caracteres.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Las contraseñas no coinciden.')
      return
    }
    setLoading(true)
    try {
      await completeRegistration(newPassword)
      endSession()
      navigate('/iniciar-sesion', { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo establecer la contraseña.')
      setLoading(false)
    }
  }

  return (
    <div className="bg-background min-h-screen flex items-center justify-center relative overflow-hidden font-body-md text-body-md">
      <div className="absolute inset-0 bg-pattern z-0" />
      <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary-fixed opacity-40 rounded-full blur-3xl z-0 pointer-events-none" />
      <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-surface-variant opacity-60 rounded-full blur-3xl z-0 pointer-events-none" />

      <main className="relative z-10 w-full max-w-[440px] px-gutter">
        <div className="bg-surface-container-lowest rounded-xl shadow-lg border border-surface-variant p-container-padding flex flex-col gap-8">
          <div className="text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-primary-container text-on-primary rounded-lg border border-outline-variant/30 flex items-center justify-center mb-6 shadow-sm">
              <Icon name="key" size="32px" filled />
            </div>
            <h1 className="font-h1-display text-h1-display text-on-surface tracking-tight">
              Establece tu contraseña
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant mt-2">
              Por seguridad, debes definir una contraseña personal antes de usar el sistema. Al
              hacerlo se cerrarán las demás sesiones y deberás volver a iniciar sesión.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            {error && (
              <div className="p-3 rounded-lg bg-error-container text-on-error-container text-sm flex items-center gap-2">
                <Icon name="error" size="18px" /> {error}
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="newPassword">
                Nueva contraseña
              </label>
              <input
                id="newPassword"
                type="password"
                required
                minLength={10}
                disabled={loading}
                placeholder="Mínimo 10 caracteres"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-surface text-on-surface border border-outline-variant rounded-lg px-4 py-2.5 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="confirmPassword">
                Confirmar contraseña
              </label>
              <input
                id="confirmPassword"
                type="password"
                required
                disabled={loading}
                placeholder="Repite la contraseña"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full bg-surface text-on-surface border border-outline-variant rounded-lg px-4 py-2.5 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 bg-primary text-on-primary font-body-lg text-body-lg font-semibold py-3 px-4 rounded-lg shadow-sm hover:bg-primary-container transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {loading ? 'Guardando...' : 'Establecer contraseña y continuar'}
              <Icon name={loading ? 'progress_activity' : 'arrow_forward'} size="20px" className={loading ? 'animate-spin' : ''} />
            </button>
          </form>
        </div>
      </main>
    </div>
  )
}
