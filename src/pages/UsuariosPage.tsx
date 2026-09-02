import { useMemo, useState, type FormEvent } from 'react'
import Icon from '@/components/ui/Icon'
import Modal from '@/components/ui/Modal'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import { getSession } from '@/utils/session'
import {
  auditRepository,
  userRepository,
  useAuditState,
  useUserState,
  type AuditRecord,
  type UserRecord,
  type UserRole,
} from '@/services/userRepository'

const roleConfig: Record<UserRole, { label: string; className: string }> = {
  admin: { label: 'Administrador', className: 'bg-primary/10 text-primary border-primary/20' },
  operator: { label: 'Vendedor', className: 'bg-surface-container-high text-on-surface-variant border-outline-variant' },
  viewer: { label: 'Supervisor', className: 'bg-secondary-fixed text-on-secondary-fixed-variant border-secondary-fixed-dim' },
}

const auditActionLabels: Record<string, string> = {
  login_success: 'Inicio de sesión',
  login_failed: 'Intento de sesión fallido',
  user_created: 'Usuario creado',
  user_updated: 'Usuario actualizado',
  user_activated: 'Usuario activado',
  user_deactivated: 'Usuario desactivado',
  profile_updated: 'Perfil actualizado',
  password_changed: 'Contraseña cambiada',
  registration_completed: 'Registro completado (cambio de contraseña inicial)',
}

function initials(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

function formatDateTime(value?: string | null) {
  if (!value) return 'Sin accesos'
  return new Intl.DateTimeFormat('es-PE', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatAuditDate(value: string) {
  return new Intl.DateTimeFormat('es-PE', {
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

export default function UsuariosPage() {
  const { users, loading, error } = useUserState()
  const { logs, loaded: auditLoaded } = useAuditState()
  const currentUserId = getSession()?.id
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<UserRecord | null>(null)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState('')
  const [changingStatus, setChangingStatus] = useState<UserRecord | null>(null)

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase()
    return users.filter(
      (user) =>
        !term ||
        user.fullName.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term) ||
        roleConfig[user.role].label.toLowerCase().includes(term),
    )
  }, [search, users])

  const openNew = () => {
    setEditing(null)
    setFormError('')
    setFormOpen(true)
  }

  const openEdit = (user: UserRecord) => {
    setEditing(user)
    setFormError('')
    setFormOpen(true)
  }

  const saveUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const fullName = String(data.get('fullName')).trim()
    const email = String(data.get('email')).trim()
    const role = String(data.get('role')) as UserRole
    const position = String(data.get('position') ?? '')
    const phone = String(data.get('phone') ?? '')

    if (!fullName || !email) {
      setFormError('Completa nombre y correo electrónico.')
      return
    }
    setSaving(true)
    setFormError('')
    try {
      if (editing) {
        await userRepository.update(editing.id, {
          fullName,
          role,
          position: position || null,
          phone: phone || null,
        })
      } else {
        const password = String(data.get('password') ?? '')
        if (password.length < 10) {
          setFormError('La contraseña debe tener al menos 10 caracteres.')
          return
        }
        await userRepository.create({
          email,
          fullName,
          password,
          role,
          position: position || null,
          phone: phone || null,
        })
      }
      setFormOpen(false)
      setEditing(null)
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : 'No se pudo guardar el usuario.')
    } finally {
      setSaving(false)
    }
  }

  const confirmStatusChange = async () => {
    if (!changingStatus) return
    const next = !changingStatus.isActive
    try {
      await userRepository.setStatus(changingStatus.id, next)
    } catch {
      // El estado en pantalla permanece sin cambios si la API rechaza la operación.
    } finally {
      setChangingStatus(null)
      void auditRepository.load(true).catch(() => undefined)
    }
  }

  if (loading && !users.length) return <LoadingState label="Cargando usuarios..." />
  if (error && !users.length) {
    return (
      <ErrorState
        title="No se pudieron cargar los usuarios"
        description={error}
      />
    )
  }

  return (
    <div className="flex flex-col gap-stack-gap">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 mb-4">
        <div>
          <h2 className="font-h1-display text-h1-display text-on-background mb-1">Usuarios</h2>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Administra el acceso del personal al sistema.
          </p>
        </div>
        <button
          type="button"
          onClick={openNew}
          className="flex items-center gap-2 bg-primary-container hover:bg-on-primary-fixed-variant text-on-primary font-body-md text-body-md font-medium py-2.5 px-5 rounded-lg shadow-sm transition-all hover:-translate-y-0.5"
        >
          <Icon name="add" size="20px" /> Crear usuario
        </button>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-surface-container-high overflow-hidden flex-1">
        <div className="p-4 border-b border-surface-container-high bg-surface-bright flex justify-end">
          <div className="relative w-full sm:w-80">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-outline">
              <Icon name="search" size="18px" />
            </span>
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              className="w-full h-10 pl-10 pr-4 bg-surface-container-highest border border-outline-variant rounded-full text-on-surface focus:ring-2 focus:ring-primary focus:outline-none"
              placeholder="Buscar usuario, correo o rol..."
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse min-w-[850px]">
            <thead>
              <tr className="border-b border-surface-container-high bg-surface-bright">
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Nombre</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Correo electrónico</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Rol</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Estado</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Último acceso</th>
                <th className="py-4 px-6 font-table-header text-table-header text-on-surface-variant uppercase text-right">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-container-high">
              {filteredUsers.map((user) => {
                const isSelf = user.id === currentUserId
                const role = roleConfig[user.role]
                return (
                  <tr key={user.id} className={`hover:bg-surface-container-low transition-colors h-[56px] group ${user.isActive ? '' : 'bg-surface-bright/50'}`}>
                    <td className="py-3 px-6 whitespace-nowrap">
                      <div className={`flex items-center gap-3 ${user.isActive ? '' : 'opacity-60'}`}>
                        <div className={`w-8 h-8 rounded-full border border-outline-variant bg-surface-variant flex items-center justify-center text-primary font-bold text-xs ${user.isActive ? '' : 'grayscale'}`}>
                          {initials(user.fullName)}
                        </div>
                        <span className="font-medium text-on-background">{user.fullName}</span>
                      </div>
                    </td>
                    <td className={`py-3 px-6 text-on-surface-variant ${user.isActive ? '' : 'opacity-60'}`}>
                      <div className="flex flex-col gap-1">
                        <span>{user.email}</span>
                        {user.mustChangePassword && (
                          <span className="inline-flex w-fit items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold border bg-secondary-fixed text-on-secondary-fixed-variant border-secondary-fixed-dim">
                            <Icon name="key" size="12px" /> Cambio de contraseña pendiente
                          </span>
                        )}
                      </div>
                    </td>
                    <td className={`py-3 px-6 ${user.isActive ? '' : 'opacity-60'}`}>
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${role.className}`}>{role.label}</span>
                    </td>
                    <td className="py-3 px-6">
                      <div className={`flex items-center gap-2 ${user.isActive ? '' : 'opacity-60'}`}>
                        <span className={`w-2 h-2 rounded-full ${user.isActive ? 'bg-green-500' : 'bg-outline'}`} />
                        <span className={user.isActive ? 'text-on-background' : 'text-on-surface-variant'}>{user.isActive ? 'Activo' : 'Inactivo'}</span>
                      </div>
                    </td>
                    <td className={`py-3 px-6 text-on-surface-variant ${user.isActive ? '' : 'opacity-60'}`}>{formatDateTime(user.lastLoginAt)}</td>
                    <td className="py-3 px-6 text-right">
                      <div className="flex items-center justify-end gap-2 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                        <button type="button" onClick={() => openEdit(user)} className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded" title="Editar">
                          <Icon name="edit" size="20px" />
                        </button>
                        {!isSelf && (
                          <button type="button" onClick={() => setChangingStatus(user)} className={`p-1.5 rounded ${user.isActive ? 'text-on-surface-variant hover:text-error hover:bg-error-container' : 'text-on-surface-variant hover:text-green-600 hover:bg-green-50'}`} title={user.isActive ? 'Desactivar' : 'Activar'}>
                            <Icon name={user.isActive ? 'block' : 'check_circle'} size="20px" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
              {filteredUsers.length === 0 && <tr><td colSpan={6} className="py-14 text-center text-on-surface-variant">No se encontraron usuarios.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-4 border-t border-surface-container-high flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Mostrando {filteredUsers.length} de {users.length} usuarios</span>
        </div>
      </div>

      <div className="bg-surface-container-lowest rounded-xl shadow-sm border border-surface-container-high overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-container-high bg-surface-bright flex items-center justify-between">
          <h3 className="font-h3-title text-h3-title text-on-surface flex items-center gap-2">
            <Icon name="verified_user" className="text-primary" /> Registro de actividad
          </h3>
          {!auditLoaded && <LoadingState label="Cargando..." />}
        </div>
        <div className="overflow-x-auto">
          {logs.length === 0 ? (
            <div className="py-8 text-center text-on-surface-variant">Sin actividad registrada.</div>
          ) : (
            <table className="w-full text-left border-collapse min-w-[700px]">
              <thead>
                <tr className="border-b border-surface-container-high bg-surface-bright">
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Fecha</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Usuario</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Acción</th>
                  <th className="py-3 px-6 font-table-header text-table-header text-on-surface-variant uppercase">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-container-high">
                {logs.slice(0, 15).map((entry) => (
                  <AuditRow key={entry.id} entry={entry} />
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editing ? 'Editar usuario' : 'Crear usuario'} icon="person" iconClassName="text-primary">
        <form key={editing?.id ?? 'new'} onSubmit={saveUser} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-lg bg-error-container text-on-error-container text-sm flex items-center gap-2">
              <Icon name="error" size="18px" /> {formError}
            </div>
          )}
          <FormField label="Nombre completo" name="fullName" defaultValue={editing?.fullName} autoFocus />
          <FormField label="Correo electrónico" name="email" type="email" defaultValue={editing?.email} disabled={Boolean(editing)} />
          <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">Rol
            <select name="role" defaultValue={editing?.role ?? 'operator'} className="h-11 px-3 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary">
              <option value="admin">Administrador</option>
              <option value="operator">Vendedor</option>
              <option value="viewer">Supervisor</option>
            </select>
          </label>
          <FormField label="Cargo" name="position" defaultValue={editing?.position ?? undefined} />
          <FormField label="Teléfono" name="phone" type="tel" defaultValue={editing?.phone ?? undefined} />
          {!editing && (
            <>
              <FormField label="Contraseña temporal" name="password" type="password" minLength={10} />
              <p className="flex items-start gap-2 rounded-lg bg-surface-container-low border border-outline-variant p-3 text-sm text-on-surface-variant">
                <Icon name="info" size="18px" className="text-primary mt-0.5" />
                El usuario deberá cambiar esta contraseña en su primer ingreso.
              </p>
            </>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setFormOpen(false)} className="h-10 px-5 rounded-lg border border-outline-variant text-primary hover:bg-surface-container-low">Cancelar</button>
            <button type="submit" disabled={saving} className="h-10 px-5 rounded-lg bg-primary-container text-on-primary hover:bg-primary disabled:opacity-60">
              {saving ? 'Guardando...' : 'Guardar usuario'}
            </button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(changingStatus)}
        title={changingStatus?.isActive ? 'Desactivar usuario' : 'Activar usuario'}
        message={`¿Deseas ${changingStatus?.isActive ? 'desactivar' : 'activar'} el acceso de ${changingStatus?.fullName ?? 'este usuario'}?`}
        confirmLabel={changingStatus?.isActive ? 'Desactivar' : 'Activar'}
        tone={changingStatus?.isActive ? 'danger' : 'default'}
        onCancel={() => setChangingStatus(null)}
        onConfirm={confirmStatusChange}
      />
    </div>
  )
}

function FormField({ label, name, type = 'text', disabled, minLength, ...props }: { label: string; name: string; type?: string; disabled?: boolean; minLength?: number; defaultValue?: string; autoFocus?: boolean }) {
  return (
    <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">
      {label}
      <input required name={name} type={type} disabled={disabled} minLength={minLength} className="h-11 px-4 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-60 disabled:cursor-not-allowed" {...props} />
    </label>
  )
}

function AuditRow({ entry }: { entry: AuditRecord }) {
  return (
    <tr className="hover:bg-surface-container-low transition-colors">
      <td className="py-3 px-6 text-on-surface-variant whitespace-nowrap">{formatAuditDate(entry.createdAt)}</td>
      <td className="py-3 px-6 text-on-surface">{entry.actorEmail ?? '—'}</td>
      <td className="py-3 px-6">
        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border bg-surface-container-high text-on-surface-variant border-outline-variant">
          {auditActionLabels[entry.action] ?? entry.action}
        </span>
      </td>
      <td className="py-3 px-6 text-on-surface-variant">{entry.description ?? entry.entityType}</td>
    </tr>
  )
}