import { useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import NotificationsPanel from '@/components/ui/NotificationsPanel'
import { useCreditState } from '@/services/creditRepository'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const navigate = useNavigate()
  const { credits } = useCreditState()

  const notificationCount = credits.filter((credit) => {
    if (credit.pendingAmount <= 0) return false
    return (
      credit.status === 'vencido' ||
      credit.risk === 'alto' ||
      credit.risk === 'critico' ||
      credit.status === 'proximo-a-vencer'
    )
  }).length

  return (
    <div className="min-h-screen bg-background">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Header
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        notificationsOpen={notificationsOpen}
        onToggleNotifications={() => setNotificationsOpen((open) => !open)}
        notificationCount={notificationCount}
      />
      <NotificationsPanel
        credits={credits}
        open={notificationsOpen}
        onClose={() => setNotificationsOpen(false)}
        onViewFiado={(id) => {
          setNotificationsOpen(false)
          navigate(`/fiados/${id}`)
        }}
      />
      <main className="w-full md:ml-[260px] pt-16 md:pt-20 px-4 md:px-container-padding pb-12">
        <Outlet />
      </main>
    </div>
  )
}