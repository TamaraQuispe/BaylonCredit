export interface Product {
  id: string
  name: string
  category: string
  price: number
  icon: string
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
  { id: 'p1', name: 'Pilsen Callao 620ml', category: 'Cervezas', price: 6.5, icon: 'local_bar' },
  { id: 'p2', name: 'Inca Kola 1.5L', category: 'Gaseosas', price: 7.0, icon: 'local_drink' },
  { id: 'p3', name: 'Cristal Lata 355ml', category: 'Cervezas', price: 4.0, icon: 'local_cafe' },
  { id: 'p4', name: 'Cusqueña Dorada 630ml', category: 'Cervezas', price: 8.5, icon: 'local_bar' },
  { id: 'p5', name: 'Coca Cola 3L', category: 'Gaseosas', price: 12.0, icon: 'local_drink' },
  { id: 'p6', name: 'Ron Cartavio 750ml', category: 'Licores', price: 45.0, icon: 'liquor' },
  { id: 'p7', name: 'Whisky Johnnie Walker 750ml', category: 'Licores', price: 120.0, icon: 'liquor' },
  { id: 'p8', name: 'Cigarrillos Marlboro', category: 'Cigarrillos', price: 14.0, icon: 'smoking_rooms' },
  { id: 'p9', name: 'Agua San Luis 600ml', category: 'Otros', price: 2.5, icon: 'water_drop' },
  { id: 'p10', name: 'Gatorade 1L', category: 'Otros', price: 6.0, icon: 'sports' },
]
