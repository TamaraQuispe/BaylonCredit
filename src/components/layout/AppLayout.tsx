import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <Header onToggleSidebar={() => setSidebarOpen((open) => !open)} />
      <main className="w-full md:ml-[260px] pt-16 md:pt-20 px-4 md:px-container-padding pb-12">
        <Outlet />
      </main>
    </div>
  )
}
