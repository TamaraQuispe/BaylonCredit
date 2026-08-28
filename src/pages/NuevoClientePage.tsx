import { Link } from 'react-router-dom'
import { useState } from 'react'

const baseInput =
  'w-full h-11 px-4 rounded-lg bg-surface-bright border border-outline-variant text-on-surface font-body-md text-body-md focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-shadow placeholder:text-outline'

export default function NuevoClientePage() {
  const [success, setSuccess] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setSuccess(true)
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-h2-headline text-h2-headline text-on-surface">Registrar Nuevo Cliente</h1>
          <p className="font-body-md text-body-md text-on-surface-variant mt-1">
            Ingrese los datos para perfilar un nuevo sujeto de crédito.
          </p>
        </div>
        <Link
          to="/clientes"
          className="hidden sm:flex items-center gap-2 text-on-surface-variant hover:text-primary transition-colors"
        >
          <span className="material-symbols-outlined text-sm">arrow_back</span>
          <span className="font-label-sm text-label-sm">Volver al listado</span>
        </Link>
      </div>

      {success && (
        <div className="mb-6 p-4 rounded-lg bg-surface-container-high border border-primary-fixed flex items-start gap-3">
          <span className="material-symbols-outlined fill-icon text-primary-container">check_circle</span>
          <div>
            <h3 className="font-h3-title text-body-lg font-semibold text-on-surface">
              Cliente registrado exitosamente
            </h3>
            <p className="font-body-md text-body-md text-on-surface-variant mt-1">
              El perfil está listo para la evaluación crediticia inicial por IA.
            </p>
          </div>
        </div>
      )}

      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm overflow-hidden">
        <form onSubmit={handleSubmit} className="p-card-padding sm:p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6">
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="nombres">
                Nombres
              </label>
              <input
                required
                id="nombres"
                name="nombres"
                type="text"
                placeholder="Ej. Juan Carlos"
                className={baseInput}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="apellidos">
                Apellidos
              </label>
              <input
                required
                id="apellidos"
                name="apellidos"
                type="text"
                placeholder="Ej. Pérez Gómez"
                className={baseInput}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="dni">
                DNI
              </label>
              <input
                required
                id="dni"
                name="dni"
                type="text"
                maxLength={8}
                pattern="[0-9]{8}"
                placeholder="8 dígitos numéricos"
                className={baseInput}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="telefono">
                Teléfono
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-on-surface-variant font-body-md text-body-md">
                  +51
                </span>
                <input
                  required
                  id="telefono"
                  name="telefono"
                  type="tel"
                  placeholder="999 999 999"
                  className={`${baseInput} pl-12`}
                />
              </div>
            </div>
            <div className="flex flex-col gap-1.5 md:col-span-2">
              <label className="font-label-sm text-label-sm text-on-surface" htmlFor="direccion">
                Dirección <span className="text-on-surface-variant font-normal">(opcional)</span>
              </label>
              <input
                id="direccion"
                name="direccion"
                type="text"
                placeholder="Dirección completa del domicilio o negocio"
                className={baseInput}
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="font-label-sm text-label-sm text-on-surface-variant" htmlFor="fecha">
                Fecha de registro
              </label>
              <div className="relative">
                <input
                  disabled
                  id="fecha"
                  name="fecha"
                  type="text"
                  value="24 de Octubre, 2023"
                  className="w-full h-11 px-4 pl-10 rounded-lg bg-surface-container-low border border-outline-variant border-dashed text-on-surface-variant font-body-md text-body-md cursor-not-allowed opacity-80"
                />
                <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-[20px]">
                  calendar_today
                </span>
              </div>
            </div>
            <div className="hidden md:block" />

            <div className="col-span-1 md:col-span-2 h-px bg-outline-variant/40 my-2" />

            <div className="col-span-1 md:col-span-2">
              <label className="flex items-start gap-3 cursor-pointer group">
                <input
                  required
                  type="checkbox"
                  className="appearance-none w-5 h-5 border-2 border-outline rounded bg-surface-bright checked:bg-primary checked:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
                />
                <span className="font-body-md text-body-md text-on-surface leading-tight select-none pt-0.5 group-hover:text-primary-container transition-colors">
                  Autorizo el tratamiento de mis datos personales según la política de privacidad y
                  evaluación de riesgo.
                </span>
              </label>
            </div>
          </div>

          <div className="mt-10 flex flex-col-reverse sm:flex-row items-center justify-end gap-4">
            <Link
              to="/clientes"
              className="w-full sm:w-auto px-6 py-2.5 rounded-lg border border-outline-variant bg-surface-container-lowest text-primary-container font-label-sm text-label-sm hover:bg-surface-container-low transition-all text-center"
            >
              Cancelar
            </Link>
            <button
              type="submit"
              className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-primary-container text-on-primary font-label-sm text-label-sm shadow-sm hover:bg-primary hover:shadow-md transition-all flex items-center justify-center gap-2"
            >
              <span className="material-symbols-outlined text-[18px]">save</span>
              Guardar cliente
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
