import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import Icon from '@/components/ui/Icon'
import { changePassword, getProfile, updateProfile, type AuthUser } from '@/services/apiClient'
import { endSession, getSession, updateSessionUser } from '@/utils/session'

const roleLabel: Record<AuthUser['role'], string> = {
  admin: 'Administrador',
  operator: 'Vendedor',
  viewer: 'Supervisor',
}

const initialProfile = {
  name: '',
  position: '',
  email: '',
  phone: '',
  createdAt: '',
}

export default function PerfilPage() {
  const navigate = useNavigate()
  const session = getSession()
  const [profile, setProfile] = useState(initialProfile)
  const [savedProfile, setSavedProfile] = useState(initialProfile)
  const [avatar, setAvatar] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [language, setLanguage] = useState('es')
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [systemAlerts, setSystemAlerts] = useState(true)
  const [message, setMessage] = useState<{ text: string; tone: 'success' | 'info' | 'error' } | null>(null)
  const [saving, setSaving] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    getProfile()
      .then((user) => {
        const loaded = {
          name: user.full_name,
          position: user.position ?? '',
          email: user.email,
          phone: user.phone ?? '',
          createdAt: user.created_at ?? '',
        }
        setProfile(loaded)
        setSavedProfile(loaded)
      })
      .catch(() => {
        if (session) {
          const loaded = {
            name: session.nombre,
            position: '',
            email: session.correo,
            phone: '',
            createdAt: '',
          }
          setProfile(loaded)
          setSavedProfile(loaded)
        }
      })
  }, [session])

  const handleAvatar = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setAvatar(String(reader.result))
    reader.readAsDataURL(file)
  }

  const saveChanges = async () => {
    setSaving(true)
    setMessage(null)
    try {
      const updated = await updateProfile({
        full_name: profile.name,
        position: profile.position || null,
        phone: profile.phone || null,
      })
      updateSessionUser(updated)
      setSavedProfile(profile)
      setMessage({ text: 'Perfil actualizado correctamente.', tone: 'success' })
    } catch (caught) {
      setMessage({
        text: caught instanceof Error ? caught.message : 'No se pudo actualizar el perfil.',
        tone: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const savePassword = async () => {
    setMessage(null)
    if (!currentPassword || !newPassword || !confirmPassword) {
      setMessage({ text: 'Ingresa la contraseña actual, la nueva y su confirmación.', tone: 'error' })
      return
    }
    if (newPassword !== confirmPassword) {
      setMessage({ text: 'Las contraseñas nuevas no coinciden.', tone: 'error' })
      return
    }
    if (newPassword.length < 10) {
      setMessage({ text: 'La nueva contraseña debe tener al menos 10 caracteres.', tone: 'error' })
      return
    }
    setSaving(true)
    try {
      await changePassword(currentPassword, newPassword)
      endSession()
      navigate('/iniciar-sesion', { replace: true })
    } catch (caught) {
      setMessage({
        text: caught instanceof Error ? caught.message : 'No se pudo cambiar la contraseña.',
        tone: 'error',
      })
    } finally {
      setSaving(false)
    }
  }

  const cancelChanges = () => {
    setProfile(savedProfile)
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setMessage({ text: 'Cambios descartados.', tone: 'info' })
  }

  const initials = profile.name
    ? profile.name
        .split(' ')
        .slice(0, 2)
        .map((part) => part[0])
        .join('')
        .toUpperCase()
    : (session?.iniciales ?? 'US')

  const memberSince = profile.createdAt
    ? new Intl.DateTimeFormat('es-PE', { month: 'short', year: 'numeric' }).format(new Date(profile.createdAt))
    : null

  return (
    <div className="max-w-5xl mx-auto w-full">
      <div className="mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-surface">Perfil de Usuario</h2>
          <p className="text-on-surface-variant mt-1 font-body-md">
            Gestiona tu información personal y preferencias de seguridad.
          </p>
        </div>
        <div className="flex gap-3">
          <button type="button" onClick={cancelChanges} className="px-4 py-2 bg-surface-container-lowest border border-outline-variant text-primary-container rounded-lg font-label-sm text-label-sm hover:bg-surface-container-low">
            Cancelar
          </button>
          <button type="button" onClick={() => void saveChanges()} disabled={saving} className="px-4 py-2 bg-primary-container text-on-primary rounded-lg font-label-sm text-label-sm hover:bg-primary shadow-sm disabled:opacity-60">
            {saving ? 'Guardando...' : 'Guardar Cambios'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-6 flex items-center gap-2 p-3 rounded-lg border ${message.tone === 'success' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : message.tone === 'error' ? 'bg-error-container text-on-error-container border-error/20' : 'bg-surface-container-low text-primary border-primary-fixed'}`}>
          <Icon name={message.tone === 'success' ? 'check_circle' : 'info'} size="20px" /> {message.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
        <div className="space-y-gutter">
          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding flex flex-col items-center text-center">
            <div className="relative mb-4 group">
              <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-surface-container-highest bg-primary-fixed flex items-center justify-center">
                {avatar ? (
                  <img src={avatar} alt="Avatar del usuario" className="w-full h-full object-cover" />
                ) : (
                  <span className="font-h1-display text-h1-display text-primary">{initials}</span>
                )}
              </div>
              <input ref={fileInput} type="file" accept="image/*" onChange={handleAvatar} className="hidden" />
              <button type="button" onClick={() => fileInput.current?.click()} className="absolute bottom-0 right-0 p-2 bg-primary-container text-on-primary rounded-full shadow-md hover:bg-primary border-2 border-white" aria-label="Cambiar foto">
                <Icon name="photo_camera" size="18px" />
              </button>
            </div>
            <h3 className="font-h3-title text-h3-title text-on-surface">{profile.name}</h3>
            <p className="font-label-sm text-label-sm text-primary font-medium mt-1 bg-surface-container-low px-3 py-1 rounded-full">
              {roleLabel[session?.rol ?? 'operator']}
            </p>
            <div className="w-full mt-6 pt-6 border-t border-outline-variant/20 flex flex-col gap-3 text-left">
              <div className="flex items-center gap-3 text-on-surface-variant"><Icon name="mail" className="text-outline" /><span className="text-sm truncate">{profile.email}</span></div>
              {memberSince && (
                <div className="flex items-center gap-3 text-on-surface-variant"><Icon name="calendar_today" className="text-outline" /><span className="text-sm">Miembro desde {memberSince}</span></div>
              )}
              {profile.position && (
                <div className="flex items-center gap-3 text-on-surface-variant"><Icon name="badge" className="text-outline" /><span className="text-sm">{profile.position}</span></div>
              )}
            </div>
          </section>
        </div>

        <div className="lg:col-span-2 space-y-gutter">
          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding">
            <SectionTitle icon="person">Información Personal</SectionTitle>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ProfileField label="Nombre Completo" value={profile.name} onChange={(value) => setProfile({ ...profile, name: value })} />
              <ProfileField label="Cargo" value={profile.position} onChange={(value) => setProfile({ ...profile, position: value })} />
              <ProfileField label="Correo Electrónico" type="email" value={profile.email} onChange={() => undefined} disabled />
              <ProfileField label="Teléfono" type="tel" value={profile.phone} onChange={(value) => setProfile({ ...profile, phone: value })} />
            </div>
          </section>

          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding">
            <SectionTitle icon="lock">Seguridad</SectionTitle>
            <p className="font-label-sm text-label-sm text-on-surface-variant mb-4 -mt-3">
              Al cambiar la contraseña, se cerrarán todas tus sesiones activas y deberás iniciar sesión nuevamente.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <PasswordInput label="Contraseña Actual" value={currentPassword} onChange={setCurrentPassword} placeholder="••••••••" />
              </div>
              <PasswordInput label="Nueva Contraseña" value={newPassword} onChange={setNewPassword} placeholder="Mínimo 10 caracteres" />
              <PasswordInput label="Confirmar Contraseña" value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirmar contraseña" />
            </div>
            <div className="flex justify-end mt-4">
              <button type="button" onClick={() => void savePassword()} disabled={saving} className="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-sm text-label-sm hover:bg-primary-container shadow-sm disabled:opacity-60">
                Cambiar contraseña
              </button>
            </div>
          </section>

          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding">
            <SectionTitle icon="tune">Preferencias</SectionTitle>
            <div className="space-y-6">
              <div className="flex items-center justify-between gap-4">
                <div><h4 className="font-body-md font-medium text-on-surface">Idioma de la Interfaz</h4><p className="font-label-sm text-label-sm text-on-surface-variant">Selecciona el idioma preferido para el panel.</p></div>
                <select value={language} onChange={(event) => setLanguage(event.target.value)} className="bg-surface-bright border border-outline-variant rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:border-primary-container min-w-[120px]"><option value="es">Español</option><option value="en">English</option></select>
              </div>
              <hr className="border-outline-variant/20" />
              <div>
                <h4 className="font-body-md font-medium text-on-surface mb-3">Notificaciones</h4>
                <div className="space-y-4">
                  <PreferenceToggle checked={emailNotifications} onChange={setEmailNotifications} title="Notificaciones por Email" description="Recibir alertas de créditos y reportes semanales en tu correo." />
                  <PreferenceToggle checked={systemAlerts} onChange={setSystemAlerts} title="Alertas del Sistema" description="Notificaciones en tiempo real sobre cambios en scorings." />
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}

function SectionTitle({ icon, children }: { icon: string; children: React.ReactNode }) {
  return <h3 className="font-h3-title text-h3-title text-on-surface mb-6 flex items-center gap-2"><Icon name={icon} className="text-primary" />{children}</h3>
}

function ProfileField({ label, value, onChange, type = 'text', disabled = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; disabled?: boolean }) {
  return <label className="space-y-1.5"><span className="font-label-sm text-label-sm text-on-surface-variant block">{label}</span><input required type={type} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} className="w-full bg-surface-bright border border-outline-variant rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container disabled:opacity-60 disabled:cursor-not-allowed" /></label>
}

function PasswordInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) {
  const [visible, setVisible] = useState(false)
  return <label className="space-y-1.5"><span className="font-label-sm text-label-sm text-on-surface-variant block">{label}</span><div className="relative"><input type={visible ? 'text' : 'password'} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="w-full bg-surface-bright border border-outline-variant rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container" /><button type="button" onClick={() => setVisible((current) => !current)} className="absolute right-3 top-1/2 -translate-y-1/2 text-outline-variant hover:text-on-surface-variant" aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}><Icon name={visible ? 'visibility' : 'visibility_off'} size="18px" /></button></div></label>
}

function PreferenceToggle({ checked, onChange, title, description }: { checked: boolean; onChange: (value: boolean) => void; title: string; description: string }) {
  return <div className="flex items-start gap-3"><button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className={`relative mt-0.5 w-10 h-5 rounded-full shrink-0 transition-colors ${checked ? 'bg-primary-container' : 'bg-outline-variant'}`}><span className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${checked ? 'translate-x-5' : ''}`} /></button><div><span className="text-sm text-on-surface block">{title}</span><span className="font-label-sm text-label-sm text-on-surface-variant">{description}</span></div></div>
}