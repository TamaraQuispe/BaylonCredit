export interface PaymentRecord {
  id: string
  client: string
  amount: number
  creditCode: string
  creditDate: string
  paidAt: string
  remainingBalance: number
  registeredBy: string
  initials: string
}

export interface PendingCredit {
  id: string
  date: string
  document: string
  amount: number
}

export interface PaymentClient {
  id: string
  initials: string
  name: string
  document: string
  profile: string
  risk: string
  credits: PendingCredit[]
}

export const paymentRecords: PaymentRecord[] = [
  { id: 'pay1', client: "Bodega 'Doña María'", amount: 450, creditCode: '#FD-1042', creditDate: '12 Oct 2023', paidAt: '25 Oct 2023, 14:30', remainingBalance: 1200, registeredBy: 'Juan C.', initials: 'JC' },
  { id: 'pay2', client: 'Minimarket El Sol', amount: 1200, creditCode: '#FD-0988', creditDate: '05 Oct 2023', paidAt: '24 Oct 2023, 09:15', remainingBalance: 0, registeredBy: 'María L.', initials: 'ML' },
  { id: 'pay3', client: 'Restobar Las Olas', amount: 300, creditCode: '#FD-1055', creditDate: '18 Oct 2023', paidAt: '24 Oct 2023, 18:45', remainingBalance: 850, registeredBy: 'Juan C.', initials: 'JC' },
  { id: 'pay4', client: 'Distribuidora Central', amount: 5000, creditCode: '#FD-1002', creditDate: '01 Sep 2023', paidAt: '23 Oct 2023, 11:20', remainingBalance: 12500, registeredBy: 'Ana P.', initials: 'AP' },
]

export const paymentClients: PaymentClient[] = [
  {
    id: 'client1',
    initials: 'CM',
    name: 'Carlos Mendoza',
    document: '45678912',
    profile: 'Cliente Regular',
    risk: 'Bajo',
    credits: [
      { id: 'credit1', date: '15/10/2023', document: 'F001-00452', amount: 450 },
      { id: 'credit2', date: '02/11/2023', document: 'F001-00510', amount: 1200 },
      { id: 'credit3', date: '20/11/2023', document: 'F001-00602', amount: 350 },
    ],
  },
  {
    id: 'client2',
    initials: 'MV',
    name: 'María Vargas',
    document: '78912345',
    profile: 'Cliente Frecuente',
    risk: 'Medio',
    credits: [
      { id: 'credit4', date: '08/11/2023', document: 'F001-00614', amount: 780 },
      { id: 'credit5', date: '16/11/2023', document: 'F001-00631', amount: 240 },
    ],
  },
  {
    id: 'client3',
    initials: 'DS',
    name: 'Empresa Distribuidora Sur S.A.C.',
    document: '20123456789',
    profile: 'Cliente Empresa',
    risk: 'Bajo',
    credits: [{ id: 'credit6', date: '01/11/2023', document: 'F001-00591', amount: 3200 }],
  },
]
