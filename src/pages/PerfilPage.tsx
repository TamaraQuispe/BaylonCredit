import { useRef, useState, type ChangeEvent } from 'react'
import Icon from '@/components/ui/Icon'

const initialProfile = {
  name: 'Juan Pérez',
  position: 'Director de Riesgos',
  email: 'juan.perez@bayloncredit.com',
  phone: '+51 987 654 321',
}

export default function PerfilPage() {
  const [profile, setProfile] = useState(initialProfile)
  const [savedProfile, setSavedProfile] = useState(initialProfile)
  const [avatar, setAvatar] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [language, setLanguage] = useState('es')
  const [emailNotifications, setEmailNotifications] = useState(true)
  const [systemAlerts, setSystemAlerts] = useState(true)
  const [message, setMessage] = useState('')
  const fileInput = useRef<HTMLInputElement>(null)

  const handleAvatar = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setAvatar(String(reader.result))
    reader.readAsDataURL(file)
  }

  const saveChanges = () => {
    if ((newPassword || confirmPassword) && newPassword !== confirmPassword) {
      setMessage('Las contraseñas nuevas no coinciden.')
      return
    }
    if (newPassword && (!currentPassword || newPassword.length < 8)) {
      setMessage('Ingresa la contraseña actual y una nueva de al menos 8 caracteres.')
      return
    }
    setSavedProfile(profile)
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setMessage('Perfil actualizado correctamente.')
  }

  const cancelChanges = () => {
    setProfile(savedProfile)
    setCurrentPassword('')
    setNewPassword('')
    setConfirmPassword('')
    setMessage('Cambios descartados.')
  }

  const initials = profile.name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

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
          <button type="button" onClick={saveChanges} className="px-4 py-2 bg-primary-container text-on-primary rounded-lg font-label-sm text-label-sm hover:bg-primary shadow-sm">
            Guardar Cambios
          </button>
        </div>
      </div>

      {message && (
        <div className={`mb-6 flex items-center gap-2 p-3 rounded-lg border ${message.includes('correctamente') ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : message.includes('descartados') ? 'bg-surface-container-low text-primary border-primary-fixed' : 'bg-error-container text-on-error-container border-error/20'}`}>
          <Icon name={message.includes('correctamente') ? 'check_circle' : 'info'} size="20px" /> {message}
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
            <p className="font-label-sm text-label-sm text-primary font-medium mt-1 bg-surface-container-low px-3 py-1 rounded-full">Administrador</p>
            <div className="w-full mt-6 pt-6 border-t border-outline-variant/20 flex flex-col gap-3 text-left">
              <div className="flex items-center gap-3 text-on-surface-variant"><Icon name="mail" className="text-outline" /><span className="text-sm truncate">{profile.email}</span></div>
              <div className="flex items-center gap-3 text-on-surface-variant"><Icon name="calendar_today" className="text-outline" /><span className="text-sm">Miembro desde Ene 2023</span></div>
            </div>
          </section>
        </div>

        <div className="lg:col-span-2 space-y-gutter">
          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding">
            <SectionTitle icon="person">Información Personal</SectionTitle>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ProfileField label="Nombre Completo" value={profile.name} onChange={(value) => setProfile({ ...profile, name: value })} />
              <ProfileField label="Cargo" value={profile.position} onChange={(value) => setProfile({ ...profile, position: value })} />
              <ProfileField label="Correo Electrónico" type="email" value={profile.email} onChange={(value) => setProfile({ ...profile, email: value })} />
              <ProfileField label="Teléfono" type="tel" value={profile.phone} onChange={(value) => setProfile({ ...profile, phone: value })} />
            </div>
          </section>

          <section className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 shadow-sm p-card-padding">
            <SectionTitle icon="lock">Seguridad</SectionTitle>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <PasswordInput label="Contraseña Actual" value={currentPassword} onChange={setCurrentPassword} placeholder="••••••••" />
              </div>
              <PasswordInput label="Nueva Contraseña" value={newPassword} onChange={setNewPassword} placeholder="Nueva contraseña" />
              <PasswordInput label="Confirmar Contraseña" value={confirmPassword} onChange={setConfirmPassword} placeholder="Confirmar contraseña" />
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

function ProfileField({ label, value, onChange, type = 'text' }: { label: string; value: string; onChange: (value: string) => void; type?: string }) {
  return <label className="space-y-1.5"><span className="font-label-sm text-label-sm text-on-surface-variant block">{label}</span><input required type={type} value={value} onChange={(event) => onChange(event.target.value)} className="w-full bg-surface-bright border border-outline-variant rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container" /></label>
}

function PasswordInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) {
  const [visible, setVisible] = useState(false)
  return <label className="space-y-1.5"><span className="font-label-sm text-label-sm text-on-surface-variant block">{label}</span><div className="relative"><input type={visible ? 'text' : 'password'} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="w-full bg-surface-bright border border-outline-variant rounded-lg px-3 py-2 pr-10 text-sm focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container" /><button type="button" onClick={() => setVisible((current) => !current)} className="absolute right-3 top-1/2 -translate-y-1/2 text-outline-variant hover:text-on-surface-variant" aria-label={visible ? 'Ocultar contraseña' : 'Mostrar contraseña'}><Icon name={visible ? 'visibility' : 'visibility_off'} size="18px" /></button></div></label>
}

function PreferenceToggle({ checked, onChange, title, description }: { checked: boolean; onChange: (value: boolean) => void; title: string; description: string }) {
  return <div className="flex items-start gap-3"><button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className={`relative mt-0.5 w-10 h-5 rounded-full shrink-0 transition-colors ${checked ? 'bg-primary-container' : 'bg-outline-variant'}`}><span className={`absolute top-1 left-1 w-3 h-3 bg-white rounded-full shadow-sm transition-transform ${checked ? 'translate-x-5' : ''}`} /></button><div><span className="text-sm text-on-surface block">{title}</span><span className="font-label-sm text-label-sm text-on-surface-variant">{description}</span></div></div>
}
