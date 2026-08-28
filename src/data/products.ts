export interface Product {
  id: string
  name: string
  category: string
  price: number
  icon: string
  stock: number
}

export const productCategories = [
  'Todos',
  'Cervezas',
  'Gaseosas',
  'Licores',
  'Cigarrillos',
  'Otros',
]

export const products: Product[] = [
  { id: 'p1', name: 'Pilsen Callao 620ml', category: 'Cervezas', price: 6.5, icon: 'sports_bar', stock: 124 },
  { id: 'p2', name: 'Inca Kola 1.5L', category: 'Gaseosas', price: 7, icon: 'local_drink', stock: 45 },
  { id: 'p3', name: 'Cristal Lata 355ml', category: 'Cervezas', price: 4, icon: 'sports_bar', stock: 82 },
  { id: 'p4', name: 'Cusqueña Dorada 630ml', category: 'Cervezas', price: 8.5, icon: 'sports_bar', stock: 31 },
  { id: 'p5', name: 'Coca Cola 3L', category: 'Gaseosas', price: 12, icon: 'local_drink', stock: 27 },
  { id: 'p6', name: 'Piscano 750ml', category: 'Licores', price: 35, icon: 'liquor', stock: 8 },
  { id: 'p7', name: 'Whisky Johnnie Walker 750ml', category: 'Licores', price: 120, icon: 'liquor', stock: 14 },
  { id: 'p8', name: 'Cigarrillos Lucky Strike', category: 'Cigarrillos', price: 12, icon: 'smoking_rooms', stock: 0 },
  { id: 'p9', name: 'Agua San Luis 600ml', category: 'Otros', price: 2.5, icon: 'water_drop', stock: 64 },
  { id: 'p10', name: 'Gatorade 1L', category: 'Otros', price: 6, icon: 'sports', stock: 11 },
]
