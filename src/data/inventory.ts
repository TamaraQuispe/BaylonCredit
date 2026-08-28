export interface InventoryItem {
  id: string
  code: string
  name: string
  category: string
  icon: string
  stock: number
  minimumStock: number
  unitCost: number
}

export const inventoryItems: InventoryItem[] = [
  {
    id: 'i1',
    code: 'BEB-001',
    name: 'Cerveza Cristal 650ml',
    category: 'Bebidas Alcohólicas',
    icon: 'sports_bar',
    stock: 124,
    minimumStock: 50,
    unitCost: 4.2,
  },
  {
    id: 'i2',
    code: 'BEB-042',
    name: 'Agua Mineral San Mateo 2.5L',
    category: 'Bebidas No Alcohólicas',
    icon: 'local_drink',
    stock: 18,
    minimumStock: 24,
    unitCost: 4.5,
  },
  {
    id: 'i3',
    code: 'COM-011',
    name: 'Hielo en cubos bolsa 3kg',
    category: 'Complementos',
    icon: 'ac_unit',
    stock: 0,
    minimumStock: 10,
    unitCost: 5,
  },
  {
    id: 'i4',
    code: 'LIC-005',
    name: 'Pisco Quebranta 750ml',
    category: 'Licores',
    icon: 'liquor',
    stock: 45,
    minimumStock: 12,
    unitCost: 29,
  },
  {
    id: 'i5',
    code: 'BEB-018',
    name: 'Gaseosa Inca Kola 1.5L',
    category: 'Bebidas No Alcohólicas',
    icon: 'local_drink',
    stock: 45,
    minimumStock: 20,
    unitCost: 5.1,
  },
  {
    id: 'i6',
    code: 'CIG-003',
    name: 'Cigarrillos Lucky Strike',
    category: 'Cigarrillos',
    icon: 'smoking_rooms',
    stock: 0,
    minimumStock: 15,
    unitCost: 9.5,
  },
]
