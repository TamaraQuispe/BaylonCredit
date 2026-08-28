import { useMemo, useState, type FormEvent } from 'react'
import Icon from '@/components/ui/Icon'
import Modal from '@/components/ui/Modal'
import ConfirmDialog from '@/components/ui/ConfirmDialog'
import { systemUsers, type SystemUser, type UserRole } from '@/data/usuarios'

const roleClasses: Record<UserRole, string> = {
  Administrador: 'bg-primary/10 text-primary border-primary/20',
  Vendedor: 'bg-surface-container-high text-on-surface-variant border-outline-variant',
  Supervisor: 'bg-secondary-fixed text-on-secondary-fixed-variant border-secondary-fixed-dim',
}

function initials(name: string) {
  return name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export default function UsuariosPage() {
  const [users, setUsers] = useState(systemUsers)
  const [search, setSearch] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<SystemUser | null>(null)
  const [changingStatus, setChangingStatus] = useState<SystemUser | null>(null)

  const filteredUsers = useMemo(() => {
    const term = search.trim().toLowerCase()
    return users.filter(
      (user) =>
        !term ||
        user.name.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term) ||
        user.role.toLowerCase().includes(term),
    )
  }, [search, users])

  const openNew = () => {
    setEditing(null)
    setFormOpen(true)
  }

  const saveUser = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const name = String(data.get('name'))
    const user: SystemUser = {
      id: editing?.id ?? `u${Date.now()}`,
      initials: initials(name),
      name,
      email: String(data.get('email')),
      role: String(data.get('role')) as UserRole,
      active: editing?.active ?? true,
      lastAccess: editing?.lastAccess ?? 'Sin accesos',
    }
    setUsers((current) =>
      editing
        ? current.map((item) => (item.id === editing.id ? user : item))
        : [...current, user],
    )
    setFormOpen(false)
    setEditing(null)
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
              {filteredUsers.map((user) => (
                <tr key={user.id} className={`hover:bg-surface-container-low transition-colors h-[56px] group ${user.active ? '' : 'bg-surface-bright/50'}`}>
                  <td className="py-3 px-6 whitespace-nowrap">
                    <div className={`flex items-center gap-3 ${user.active ? '' : 'opacity-60'}`}>
                      <div className={`w-8 h-8 rounded-full border border-outline-variant bg-surface-variant flex items-center justify-center text-primary font-bold text-xs ${user.active ? '' : 'grayscale'}`}>
                        {user.initials}
                      </div>
                      <span className="font-medium text-on-background">{user.name}</span>
                    </div>
                  </td>
                  <td className={`py-3 px-6 text-on-surface-variant ${user.active ? '' : 'opacity-60'}`}>{user.email}</td>
                  <td className={`py-3 px-6 ${user.active ? '' : 'opacity-60'}`}>
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${roleClasses[user.role]}`}>{user.role}</span>
                  </td>
                  <td className="py-3 px-6">
                    <div className={`flex items-center gap-2 ${user.active ? '' : 'opacity-60'}`}>
                      <span className={`w-2 h-2 rounded-full ${user.active ? 'bg-green-500' : 'bg-outline'}`} />
                      <span className={user.active ? 'text-on-background' : 'text-on-surface-variant'}>{user.active ? 'Activo' : 'Inactivo'}</span>
                    </div>
                  </td>
                  <td className={`py-3 px-6 text-on-surface-variant ${user.active ? '' : 'opacity-60'}`}>{user.lastAccess}</td>
                  <td className="py-3 px-6 text-right">
                    <div className="flex items-center justify-end gap-2 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-opacity">
                      <button type="button" onClick={() => { setEditing(user); setFormOpen(true) }} className="p-1.5 text-on-surface-variant hover:text-primary hover:bg-surface-container rounded" title="Editar">
                        <Icon name="edit" size="20px" />
                      </button>
                      <button type="button" onClick={() => setChangingStatus(user)} className={`p-1.5 rounded ${user.active ? 'text-on-surface-variant hover:text-error hover:bg-error-container' : 'text-on-surface-variant hover:text-green-600 hover:bg-green-50'}`} title={user.active ? 'Desactivar' : 'Activar'}>
                        <Icon name={user.active ? 'block' : 'check_circle'} size="20px" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredUsers.length === 0 && <tr><td colSpan={6} className="py-14 text-center text-on-surface-variant">No se encontraron usuarios.</td></tr>}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-4 border-t border-surface-container-high flex items-center justify-between">
          <span className="font-label-sm text-label-sm text-on-surface-variant">Mostrando {filteredUsers.length} de {users.length} usuarios</span>
          <div className="flex gap-2"><button type="button" disabled className="px-3 py-1 border border-outline-variant rounded-md text-on-surface-variant disabled:opacity-50">Anterior</button><button type="button" disabled className="px-3 py-1 border border-outline-variant rounded-md text-on-surface-variant disabled:opacity-50">Siguiente</button></div>
        </div>
      </div>

      <Modal open={formOpen} onClose={() => setFormOpen(false)} title={editing ? 'Editar usuario' : 'Crear usuario'} icon="person" iconClassName="text-primary">
        <form key={editing?.id ?? 'new'} onSubmit={saveUser} className="space-y-4">
          <UserField label="Nombre completo" name="name" defaultValue={editing?.name} />
          <UserField label="Correo electrónico" name="email" type="email" defaultValue={editing?.email} />
          <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">Rol
            <select name="role" defaultValue={editing?.role ?? 'Vendedor'} className="h-11 px-3 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary">
              <option>Administrador</option><option>Supervisor</option><option>Vendedor</option>
            </select>
          </label>
          {!editing && <UserField label="Contraseña temporal" name="password" type="password" minLength={8} />}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setFormOpen(false)} className="h-10 px-5 rounded-lg border border-outline-variant text-primary hover:bg-surface-container-low">Cancelar</button>
            <button type="submit" className="h-10 px-5 rounded-lg bg-primary-container text-on-primary hover:bg-primary">Guardar usuario</button>
          </div>
        </form>
      </Modal>

      <ConfirmDialog
        open={Boolean(changingStatus)}
        title={changingStatus?.active ? 'Desactivar usuario' : 'Activar usuario'}
        message={`¿Deseas ${changingStatus?.active ? 'desactivar' : 'activar'} el acceso de ${changingStatus?.name ?? 'este usuario'}?`}
        confirmLabel={changingStatus?.active ? 'Desactivar' : 'Activar'}
        tone={changingStatus?.active ? 'danger' : 'default'}
        onCancel={() => setChangingStatus(null)}
        onConfirm={() => {
          if (changingStatus) setUsers((current) => current.map((user) => user.id === changingStatus.id ? { ...user, active: !user.active } : user))
          setChangingStatus(null)
        }}
      />
    </div>
  )
}

function UserField({ label, name, type = 'text', ...props }: { label: string; name: string; type?: string; defaultValue?: string; minLength?: number }) {
  return <label className="flex flex-col gap-1.5 font-label-sm text-label-sm text-on-surface">{label}<input required name={name} type={type} className="h-11 px-4 rounded-lg bg-surface border border-outline-variant focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary" {...props} /></label>
}
