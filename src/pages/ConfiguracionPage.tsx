import { useState, type FormEvent } from 'react'
import Icon from '@/components/ui/Icon'
import Modal from '@/components/ui/Modal'

export default function ConfiguracionPage() {
  const [business, setBusiness] = useState({
    name: 'Cervecería Baylón',
    phone: '+51 987 654 321',
    address: 'Av. Principal 123, Lima, Perú',
  })
  const [editingBusiness, setEditingBusiness] = useState(false)
  const [passwordOpen, setPasswordOpen] = useState(false)
  const [privacyOpen, setPrivacyOpen] = useState(false)
  const [twoFactor, setTwoFactor] = useState(false)
  const [term, setTerm] = useState('15')
  const [maxAmount, setMaxAmount] = useState('200.00')
  const [alerts, setAlerts] = useState(true)
  const [notice, setNotice] = useState('')

  const showNotice = (message: string) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 2500)
  }

  const updatePassword = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setPasswordOpen(false)
    showNotice('Contraseña actualizada correctamente.')
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8 pb-12">
      <div>
        <h2 className="font-h1-display text-h1-display text-on-surface mb-2">Configuración</h2>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Gestiona las preferencias y parámetros generales del sistema.
        </p>
      </div>

      {notice && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200">
          <Icon name="check_circle" size="20px" /> {notice}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
        <section className="md:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-h3-title text-h3-title flex items-center gap-2">
              <Icon name="storefront" className="text-primary" /> Datos del negocio
            </h3>
            <button
              type="button"
              onClick={() => {
                if (editingBusiness) showNotice('Datos del negocio guardados.')
                setEditingBusiness((editing) => !editing)
              }}
              className="text-primary hover:bg-surface-container-low px-3 py-1.5 rounded-lg font-label-sm text-label-sm flex items-center gap-1"
            >
              <Icon name={editingBusiness ? 'save' : 'edit'} size="16px" />
              {editingBusiness ? 'Guardar' : 'Editar'}
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <SettingInput label="Nombre comercial" value={business.name} readOnly={!editingBusiness} onChange={(value) => setBusiness({ ...business, name: value })} />
            <SettingInput label="Teléfono" value={business.phone} readOnly={!editingBusiness} onChange={(value) => setBusiness({ ...business, phone: value })} />
            <div className="sm:col-span-2">
              <SettingInput label="Dirección" value={business.address} readOnly={!editingBusiness} onChange={(value) => setBusiness({ ...business, address: value })} />
            </div>
          </div>
        </section>

        <section className="md:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding flex flex-col">
          <h3 className="font-h3-title text-h3-title mb-6 flex items-center gap-2">
            <Icon name="security" className="text-primary" /> Seguridad
          </h3>
          <div className="space-y-4 flex-1">
            <button type="button" onClick={() => setPasswordOpen(true)} className="w-full bg-surface-bright border border-outline-variant hover:bg-surface-container-low hover:border-primary text-primary px-4 py-3 rounded-lg flex items-center justify-between group">
              <span className="font-label-sm text-label-sm">Cambiar contraseña</span>
              <Icon name="chevron_right" className="text-outline-variant group-hover:text-primary" />
            </button>
            <div className="p-4 bg-surface-bright rounded-lg border border-outline-variant">
              <div className="flex justify-between items-start mb-2">
                <span className="font-label-sm text-label-sm font-semibold text-on-surface">Doble factor (2FA)</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${twoFactor ? 'bg-emerald-100 text-emerald-700' : 'bg-surface-container-high text-on-surface-variant'}`}>
                  {twoFactor ? 'ACTIVO' : 'INACTIVO'}
                </span>
              </div>
              <p className="text-xs text-on-surface-variant mb-3">Mayor seguridad para las aprobaciones de crédito.</p>
              <button type="button" onClick={() => { setTwoFactor((active) => !active); showNotice(`Doble factor ${twoFactor ? 'desactivado' : 'activado'}.`) }} className="text-primary font-label-sm text-label-sm hover:underline">
                {twoFactor ? 'Desactivar' : 'Configurar ahora'}
              </button>
            </div>
          </div>
        </section>

        <section className="md:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
          <h3 className="font-h3-title text-h3-title mb-6 flex items-center gap-2">
            <Icon name="request_quote" className="text-primary" /> Configuración de fiados
          </h3>
          <div className="space-y-6">
            <SettingRow title="Plazo predeterminado" description="Días estándar para nuevos créditos">
              <select value={term} onChange={(event) => setTerm(event.target.value)} className="w-32 bg-surface-bright border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:ring-2 focus:ring-primary outline-none">
                <option value="7">7 días</option><option value="15">15 días</option><option value="30">30 días</option>
              </select>
            </SettingRow>
            <hr className="border-outline-variant" />
            <SettingRow title="Monto máximo general" description="Límite por defecto sin IA">
              <div className="relative w-40">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">S/</span>
                <input value={maxAmount} onChange={(event) => setMaxAmount(event.target.value)} inputMode="decimal" className="w-full bg-surface-bright border border-outline-variant rounded-lg pl-8 pr-4 py-2 text-right focus:ring-2 focus:ring-primary outline-none" />
              </div>
            </SettingRow>
            <hr className="border-outline-variant" />
            <SettingRow title="Alertas de vencimiento" description="Notificar 2 días antes">
              <Toggle checked={alerts} onChange={setAlerts} label="Alertas de vencimiento" />
            </SettingRow>
            <button type="button" onClick={() => showNotice('Parámetros de fiados guardados.')} className="w-full py-2.5 bg-primary-container text-on-primary rounded-lg hover:bg-primary font-medium">
              Guardar parámetros
            </button>
          </div>
        </section>

        <section className="md:col-span-6 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-sm p-card-padding">
          <h3 className="font-h3-title text-h3-title mb-6 flex items-center gap-2">
            <Icon name="policy" className="text-primary" /> Privacidad y datos
          </h3>
          <div className="flex flex-col h-[calc(100%-3rem)] justify-between">
            <p className="font-body-md text-body-md text-on-surface-variant mb-6">
              Administra los permisos y consentimientos relacionados con el tratamiento de datos personales de tus clientes para el análisis de riesgo crediticio.
            </p>
            <button type="button" onClick={() => setPrivacyOpen(true)} className="w-full flex justify-between items-center bg-surface-container-low hover:bg-surface-container p-4 rounded-lg border border-primary/20 text-primary group">
              <div className="flex items-center gap-3 text-left">
                <Icon name="description" />
                <span className="font-label-sm text-label-sm font-semibold">Gestión de autorización para tratamiento de datos personales</span>
              </div>
              <Icon name="arrow_forward" className="group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </section>
      </div>

      <Modal open={passwordOpen} onClose={() => setPasswordOpen(false)} title="Cambiar contraseña" icon="lock" iconClassName="text-primary">
        <form onSubmit={updatePassword} className="space-y-4">
          <PasswordField label="Contraseña actual" name="current-password" />
          <PasswordField label="Nueva contraseña" name="new-password" />
          <PasswordField label="Confirmar contraseña" name="confirm-password" />
          <div className="flex justify-end gap-3"><button type="button" onClick={() => setPasswordOpen(false)} className="h-10 px-5 border border-outline-variant rounded-lg text-primary">Cancelar</button><button type="submit" className="h-10 px-5 bg-primary-container text-on-primary rounded-lg">Actualizar</button></div>
        </form>
      </Modal>

      <Modal open={privacyOpen} onClose={() => setPrivacyOpen(false)} title="Privacidad y autorizaciones" icon="policy" iconClassName="text-primary" maxWidth="max-w-lg">
        <div className="space-y-4">
          <ConsentOption title="Evaluación crediticia con IA" description="Permite analizar el historial transaccional para calcular el riesgo." defaultChecked />
          <ConsentOption title="Notificaciones de cobranza" description="Autoriza recordatorios de vencimiento por teléfono o mensajería." defaultChecked />
          <ConsentOption title="Uso estadístico anonimizado" description="Utiliza datos sin identificación para mejorar los reportes." />
          <div className="flex justify-end gap-3 pt-2"><button type="button" onClick={() => setPrivacyOpen(false)} className="h-10 px-5 border border-outline-variant rounded-lg text-primary">Cancelar</button><button type="button" onClick={() => { setPrivacyOpen(false); showNotice('Preferencias de privacidad guardadas.') }} className="h-10 px-5 bg-primary-container text-on-primary rounded-lg">Guardar</button></div>
        </div>
      </Modal>
    </div>
  )
}

function SettingInput({ label, value, readOnly, onChange }: { label: string; value: string; readOnly: boolean; onChange: (value: string) => void }) {
  return <label className="block font-label-sm text-label-sm text-on-surface-variant">{label}<input value={value} readOnly={readOnly} onChange={(event) => onChange(event.target.value)} className={`mt-1 w-full border border-outline-variant rounded-lg px-4 py-2 text-on-surface focus:ring-2 focus:ring-primary outline-none ${readOnly ? 'bg-surface-bright' : 'bg-white border-primary'}`} /></label>
}

function SettingRow({ title, description, children }: { title: string; description: string; children: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-4"><div><p className="font-label-sm text-label-sm text-on-surface font-semibold mb-1">{title}</p><p className="text-xs text-on-surface-variant">{description}</p></div>{children}</div>
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return <button type="button" role="switch" aria-checked={checked} aria-label={label} onClick={() => onChange(!checked)} className={`relative w-11 h-6 rounded-full transition-colors ${checked ? 'bg-primary' : 'bg-outline-variant'}`}><span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white border transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`} /></button>
}

function PasswordField({ label, name }: { label: string; name: string }) {
  return <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">{label}<input required minLength={8} name={name} type="password" className="h-11 px-4 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary" /></label>
}

function ConsentOption({ title, description, defaultChecked = false }: { title: string; description: string; defaultChecked?: boolean }) {
  return <label className="flex items-start gap-3 p-3 rounded-lg border border-outline-variant bg-surface-bright cursor-pointer"><input type="checkbox" defaultChecked={defaultChecked} className="mt-1 rounded border-outline-variant text-primary focus:ring-primary" /><span><span className="block font-medium text-on-surface">{title}</span><span className="text-sm text-on-surface-variant">{description}</span></span></label>
}
