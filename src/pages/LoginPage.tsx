import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { startSession } from '@/utils/session'
import { login } from '@/services/apiClient'
import {
  webauthnAuthenticationBegin,
  webauthnAuthenticationFinish,
} from '@/services/apiClient'
import { base64UrlToBuffer, bufferToBase64Url } from '@/utils/base64url'
import Icon from '@/components/ui/Icon'

const LOGO =
  'https://lh3.googleusercontent.com/aida/AEtjO1UxLP1I1dimD3MckhOYQJf9cPSVRJtIPwkBFB6KVAkoj5Oy_QKoRSj4nZNFmef63FNZS-iOWSvn8k5SsG_Ra75_DdXtfYhmOyiQo_Wckl_8_1jaxYhXRubg0PPDE9tXem8Vy7ahwSCS4_tNTmU0GbYc0CZRIcY-dNseMIPWDH1I_PhFEyyDC8GnGYsO90xiryUVf83SL68T3Bb-FkYwF1-1dnbDhxxrdcfh4sooKZfRJl3rivUQhGhfO3E'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [remember, setRemember] = useState(false)
  const [role, setRole] = useState<'administrador' | 'cajero'>('administrador')
  const [loading, setLoading] = useState(false)
  const [webauthnLoading, setWebauthnLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await login(email.trim(), password)
      startSession(response.access_token, response.refresh_token, response.user, remember)
      navigate('/inicio')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo iniciar sesión.')
    } finally {
      setLoading(false)
    }
  }

  async function handleWebauthn() {
    const mediator = (navigator as { credentials?: WebauthnNavigatorCredentials }).credentials
    if (!mediator || typeof mediator.get === 'undefined') {
      setError('Tu navegador no soporta llaves FIDO2 / WebAuthn.')
      return
    }
    setWebauthnLoading(true)
    setError('')
    try {
      const { session_id, options } = await webauthnAuthenticationBegin(undefined)
      const challengeB64 = String(options.challenge)
      const requestOptions: WebauthnRequestOptions = {
        challenge: base64UrlToBuffer(challengeB64),
        rpId: String(options.rpId || window.location.hostname),
        timeout: Number(options.timeout || 120000),
        userVerification: String(options.userVerification || 'preferred'),
      }
      if (Array.isArray(options.allowCredentials) && options.allowCredentials.length > 0) {
        requestOptions.allowCredentials = (options.allowCredentials as { id: string }[]).map(
          (entry) => ({ id: base64UrlToBuffer(entry.id), type: 'public-key' }),
        )
      }
      const credential = await mediator.get(requestOptions)
      if (!credential) {
        setError('No se detectó ninguna llave. Inténtalo de nuevo.')
        return
      }

      const rawId = credential.rawId ?? credential.id
      const userHandle = credential.response.userHandle

      const serialized: Record<string, unknown> = {
        id: bufferToBase64Url(rawId),
        rawId: bufferToBase64Url(rawId),
        type: credential.type,
        authenticatorAttachment: credential.authenticatorAttachment,
        clientExtensionResults: {},
        response: {
          authenticatorData: bufferToBase64Url(credential.response.authenticatorData as ArrayBuffer),
          clientDataJSON: bufferToBase64Url(credential.response.clientDataJSON),
          signature: credential.response.signature
            ? bufferToBase64Url(credential.response.signature)
            : null,
          userHandle: userHandle ? bufferToBase64Url(userHandle) : null,
        },
      }

      const response = await webauthnAuthenticationFinish(
        session_id,
        challengeB64,
        userHandle ? bufferToBase64Url(userHandle) : '',
        serialized,
      )
      startSession(response.access_token, response.refresh_token, response.user, true)
      navigate('/inicio')
    } catch (caught) {
      const message =
        caught instanceof Error ? caught.message : 'No se pudo autenticar con la llave.'
      setError(/canceled|cancelled|abort/i.test(message) ? 'Autenticación cancelada.' : message)
    } finally {
      setWebauthnLoading(false)
    }
  }

  return (
    <div className="bg-background min-h-screen grid grid-cols-1 lg:grid-cols-12 font-body-md text-body-md antialiased">
      {/* PANEL IZQUIERDO: Brand & Value Showcase */}
      <section className="lg:col-span-7 bg-[#0f172a] relative overflow-hidden flex flex-col justify-between p-8 sm:p-12 lg:p-16 text-white border-b lg:border-b-0 lg:border-r border-slate-800">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#1e3a8a] rounded-full blur-3xl opacity-40 pointer-events-none" />
        <div className="absolute top-1/2 -right-24 w-80 h-80 bg-[#f59e0b] rounded-full blur-3xl opacity-20 pointer-events-none" />
        <div className="absolute bottom-0 left-1/4 w-96 h-72 bg-[#38bdf8] rounded-full blur-3xl opacity-15 pointer-events-none" />

        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 p-0.5">
              <img alt="Isotipo BaylonCredit" src={LOGO} className="w-full h-full object-cover rounded-[10px]" />
            </div>
            <div>
              <span className="text-base sm:text-lg font-bold tracking-tight text-white flex items-center gap-1.5">
                BaylonCredit{' '}
                <span className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold tracking-wider bg-[#38bdf8]/20 text-[#38bdf8] border border-[#38bdf8]/30">
                  IA Suite
                </span>
              </span>
              <p className="text-xs text-slate-400 font-medium">Cervecería Baylón • División Créditos</p>
            </div>
          </div>
          <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs text-slate-300 backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Motor IA Activo v2.4
          </span>
        </div>

        <div className="relative z-10 my-10 lg:my-0 max-w-xl">
          <div className="relative inline-block mb-6 group">
            <div className="w-28 h-28 sm:w-32 sm:h-32 rounded-3xl overflow-hidden shadow-2xl shadow-blue-950/80 ring-1 ring-white/20 transition-transform duration-500 group-hover:scale-105 bg-slate-900/60 backdrop-blur-sm p-1">
              <img alt="Logotipo Oficial BaylonCredit IA" src={LOGO} className="w-full h-full object-contain drop-shadow-xl" />
            </div>
            <div className="absolute -bottom-2 -right-2 bg-gradient-to-r from-amber-500 to-amber-600 text-slate-950 text-[11px] font-bold px-2.5 py-1 rounded-full shadow-lg flex items-center gap-1">
              <Icon name="verified" size="12px" />
              Libreta Digital
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight mb-4">
            El cuaderno de fiados{' '}
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 via-amber-200 to-sky-400">
              inteligente
            </span>{' '}
            para Cervecería Baylón
          </h1>
          <p className="text-slate-300 text-base sm:text-lg leading-relaxed font-normal mb-8 max-w-lg">
            Control de créditos comerciales, evaluación de riesgo en tiempo real impulsada por IA y digitalización integral
            del fiado cervecero sin pérdidas de stock ni cobranzas manuales.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-md">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-[#38bdf8] mb-1">
                <Icon name="auto_awesome" size="16px" />
                99.4% Precisión
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">Evaluación algorítmica de mora y comportamiento cervecero</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-md">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400 mb-1">
                <Icon name="payments" size="16px" />
                S/ 48,500+
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">Fiados gestionados y recuperados puntualmente</p>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800/90 backdrop-blur-md">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400 mb-1">
                <Icon name="cloud_done" size="16px" />
                100% Cero Papel
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">Libreta física obsoleta: sincronización en la nube</p>
            </div>
          </div>
        </div>

        <div className="relative z-10 pt-6 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Icon name="shield_lock" size="16px" className="text-amber-400" />
            <span>Cifrado bancario TLS 1.3 de punto a punto</span>
          </div>
          <span className="text-[11px] text-slate-500 font-mono">B-CREDIT//2024</span>
        </div>
      </section>

      {/* PANEL DERECHO: Formulario de Acceso */}
      <section className="lg:col-span-5 bg-surface-bright flex flex-col justify-center items-center p-6 sm:p-10 lg:p-12 relative">
        <div className="w-full max-w-md">
          <div className="bg-surface-container-lowest rounded-2xl shadow-xl shadow-slate-200/60 border border-surface-container-high/80 p-6 sm:p-8">
            <div className="mb-6">
              <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-primary-fixed text-primary text-xs font-semibold mb-3">
                <Icon name="verified_user" size="14px" />
                Portal Administrativo Seguro
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-on-surface tracking-tight">Bienvenido de nuevo</h2>
              <p className="text-sm text-on-surface-variant mt-1.5">
                Ingresa tus credenciales para gestionar fiados, autorizaciones y pagos.
              </p>
            </div>

            <div className="mb-6 p-1 bg-surface-container rounded-xl grid grid-cols-2 gap-1 text-xs font-semibold">
              <button
                type="button"
                onClick={() => setRole('administrador')}
                className={`py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5 ${role === 'administrador' ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}
              >
                <Icon name="manage_accounts" size="16px" />
                Dueño / Gerencia
              </button>
              <button
                type="button"
                onClick={() => setRole('cajero')}
                className={`py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5 ${role === 'cajero' ? 'bg-surface-container-lowest text-primary shadow-sm' : 'text-on-surface-variant hover:text-on-surface'}`}
              >
                <Icon name="point_of_sale" size="16px" />
                Caja y Despacho
              </button>
            </div>
            <p className="text-[11px] text-on-surface-variant mt-2 mb-2 flex items-start gap-1.5">
              <Icon name="info" size="14px" className="text-outline shrink-0" />
              <span>
                {role === 'administrador'
                  ? 'Acceso con análisis de riesgo, reportes y administración de usuarios.'
                  : 'Acceso operativo: ventas, fiados, clientes, productos y pagos en caja.'}
              </span>
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="p-3 rounded-lg bg-error-container text-on-error-container text-sm flex items-center gap-2">
                  <Icon name="error" size="18px" /> {error}
                </div>
              )}

              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-on-surface" htmlFor="email">
                  Correo institucional
                </label>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-outline">
                    <Icon name="alternate_email" size="18px" />
                  </span>
                  <input
                    id="email"
                    type="email"
                    required
                    disabled={loading}
                    placeholder="usuario@baylon.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/60 rounded-xl pl-10 pr-4 py-2.5 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-outline/70 shadow-sm"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="block text-xs font-medium text-on-surface" htmlFor="password">
                    Contraseña
                  </label>
                  <button
                    type="button"
                    className="text-xs font-medium text-primary hover:text-primary-container hover:underline transition-colors"
                  >
                    ¿Olvidaste tu clave?
                  </button>
                </div>
                <div className="relative">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-outline">
                    <Icon name="lock" size="18px" />
                  </span>
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    disabled={loading}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-surface-container-lowest text-on-surface text-sm border border-outline-variant/60 rounded-xl pl-10 pr-10 py-2.5 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all placeholder:text-outline/70 shadow-sm"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    title={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-outline hover:text-on-surface transition-colors"
                  >
                    <Icon name={showPassword ? 'visibility_off' : 'visibility'} size="18px" />
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer group">
                  <input
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="w-4 h-4 text-primary bg-surface border-outline-variant rounded focus:ring-primary focus:ring-2 cursor-pointer"
                  />
                  <span className="text-xs text-on-surface-variant group-hover:text-on-surface transition-colors font-medium">
                    Recordar sesión en este equipo
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className={`w-full mt-2 bg-[#1e3a8a] hover:bg-[#00236f] text-white font-semibold text-sm py-3 px-4 rounded-xl shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2 active:scale-[0.99] group disabled:opacity-60 disabled:cursor-not-allowed`}
              >
                <span>{loading ? 'Ingresando...' : role === 'administrador' ? 'Ingresar a BaylonCredit IA' : 'Ingresar a la caja'}</span>
                <Icon name={loading ? 'progress_activity' : 'arrow_forward'} size="18px" className={loading ? 'animate-spin' : ''} />
              </button>

              <button
                type="button"
                onClick={handleWebauthn}
                disabled={webauthnLoading || loading}
                className="w-full bg-surface-container-low hover:bg-surface-container text-on-surface font-medium text-xs py-2.5 px-3 rounded-xl border border-outline-variant/40 transition-colors flex items-center justify-center gap-2 text-center disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <Icon name={webauthnLoading ? 'progress_activity' : 'key'} size="16px" className={`${webauthnLoading ? 'animate-spin' : ''} text-amber-600`} />
                <span>{webauthnLoading ? 'Esperando llave FIDO2...' : 'Acceder con llave de seguridad física / FIDO2'}</span>
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-surface-container-high flex items-center justify-center gap-2 text-center text-xs text-outline">
              <Icon name="verified" size="16px" className="text-primary" />
              <span>Acceso cifrado y registrado por políticas de auditoría</span>
            </div>
          </div>

          <div className="text-center mt-6 space-y-1">
            <p className="text-xs text-on-surface-variant font-medium">
              Cervecería Baylón © 2024 • Todos los derechos reservados
            </p>
            <p className="text-[11px] text-outline">Sistema interno para personal autorizado y clientes registrados.</p>
          </div>
        </div>
      </section>
    </div>
  )
}