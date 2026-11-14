import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const base = 'https://demo-credify.168-75-71-113.sslip.io'
const output = process.argv[2]
if (!output || !process.env.DEMO_USER_PASSWORD) throw Error('Demo password and output required')
await mkdir(output, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'es-PE', timezoneId: 'America/Lima' })
page.setDefaultTimeout(30000)
const results = []
const started = new Date().toISOString()
let token

async function api(route, body, expected = 200) {
  const response = await page.request.fetch(base + '/api/v1' + route, {
    method: body ? 'POST' : 'GET', headers: { Authorization: `Bearer ${token}` },
    ...(body ? { data: body } : {}),
  })
  assert.equal(response.status(), expected, route)
  return response.json()
}

async function capture(name) { await page.screenshot({ path: path.join(output, name), fullPage: true }) }

try {
  await page.goto(base + '/iniciar-sesion')
  await page.locator('#email').fill('docente@example.com')
  await page.locator('#password').fill(process.env.DEMO_USER_PASSWORD)
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  await page.waitForURL('**/inicio')
  token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('credify_auth_session') || localStorage.getItem('credify_auth_session')).accessToken)
  const serial = String(Date.now()).slice(-7)
  const business = 'DEMO - Revisión R ' + serial
  const clients = []
  for (const document of ['8' + serial, '7' + serial]) {
    clients.push(await api('/clients', {
      first_name: 'Cliente', last_name: 'Mejoras APF2', business_name: business,
      document, phone: '000000000', address: 'Prueba ficticia',
    }, 201))
  }
  const loaded = await api('/clients')
  const shared = loaded.filter(client => client.business_name === business)
  assert.equal(shared.length, 2)
  assert.notEqual(shared[0].id, shared[1].id)
  assert.notEqual(shared[0].document, shared[1].document)
  assert.equal(new Set(loaded.map(client => client.id)).size, loaded.length)
  assert.equal(new Set(loaded.map(client => client.document)).size, loaded.length)
  results.push({ card: 'R03', passed: true, detail: 'Nombres compartidos con IDs/documentos distintos; no se borraron clientes.' })
  await page.goto(base + '/clientes', { waitUntil: 'networkidle' })
  const counter = await page.getByRole('button', { name: /^Todos los clientes/ }).innerText()
  assert.ok(counter.trim().endsWith(String(loaded.length)))
  results.push({ card: 'R02', passed: true, detail: 'Contador coincide con los clientes cargados.' })
  await page.getByPlaceholder('Buscar por nombre, DNI o teléfono...').fill(clients[0].document)
  const detail = page.getByRole('link', { name: 'Ver detalle de ' + business, exact: true })
  await detail.waitFor()
  assert.equal(await detail.evaluate(link => getComputedStyle(link.parentElement).opacity), '1')
  assert.equal(await page.getByRole('button', { name: 'Editar: no disponible en este MVP' }).isDisabled(), true)
  await capture('R01-R02-R03-clientes.png')
  await detail.click()
  await page.waitForURL('**/clientes/' + clients[0].id)
  results.push({ card: 'R01', passed: true, detail: 'Detalle accesible sin hover; edición no implementada explícitamente deshabilitada.' })

  await page.goto(base + '/evaluacion-crediticia?cliente=' + clients[0].id, { waitUntil: 'networkidle' })
  await page.getByLabel('Monto a evaluar').fill('50')
  await page.getByRole('button', { name: 'Evaluar crédito', exact: true }).click()
  await page.getByRole('button', { name: 'Recalcular', exact: true }).waitFor()
  await page.getByText('Historial limitado', { exact: true }).waitFor()
  await page.getByText('Indicador por reglas', { exact: true }).waitFor()
  await capture('R07-historial-limitado.png')
  results.push({ card: 'R07', passed: true, detail: 'Advertencia de historial limitado; indicador no presentado como probabilidad validada. Backend conserva decisión por reglas.' })

  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Lima' })
  const credit = await api('/credits', { client_id: clients[0].id, amount: '50', credit_date: today }, 201)
  await page.goto(base + '/creditos', { waitUntil: 'networkidle' })
  const row = page.getByRole('row').filter({ hasText: business }).filter({ hasText: 'Vence en 1 día' })
  await row.first().waitFor()
  await capture('R04-listado-vencimiento.png')
  await page.goto(base + '/creditos/' + credit.id, { waitUntil: 'networkidle' })
  await page.getByText('Falta 1 día', { exact: true }).waitFor()
  await capture('R04-detalle-vencimiento.png')
  results.push({ card: 'R04', passed: true, detail: 'Vencimiento mañana: listado Vence en 1 día y detalle Falta 1 día.' })

  await page.goto(base + '/pagos/nuevo?cliente=' + clients[0].id + '&credito=' + credit.id, { waitUntil: 'networkidle' })
  await page.waitForFunction(id => document.querySelector('#payment-client')?.value === id, clients[0].id)
  assert.equal(await page.locator('#payment-amount').inputValue(), '')
  assert.equal(await page.getByRole('button', { name: 'Confirmar Pago', exact: true }).isDisabled(), true)
  await page.getByRole('button', { name: 'Pagar deuda total', exact: true }).click()
  assert.equal(Number(await page.locator('#payment-amount').inputValue()), 50)
  await page.locator('#payment-amount').fill('20')
  await capture('R05-abono-explicito.png')
  await page.getByRole('button', { name: 'Confirmar Pago', exact: true }).click()
  await page.getByRole('heading', { name: 'Pago registrado correctamente' }).waitFor()
  const saved = await api('/credits/' + credit.id)
  assert.equal(Number(saved.pending_amount), 30)
  await capture('R05-confirmacion-abono.png')
  results.push({ card: 'R05', passed: true, detail: 'Monto inicial vacío; total por acción expresa; abono UI S/20 persiste saldo S/30.' })

  await page.goto(base + '/pagos', { waitUntil: 'networkidle' })
  const paymentRow = page.getByRole('row').filter({ hasText: business }).first()
  await paymentRow.waitFor()
  assert.match(await paymentRow.innerText(), /\d{2}\/\d{2}\/\d{4}, \d{2}:\d{2}/)
  await capture('R06-fechas-pagos.png')
  results.push({ card: 'R06', passed: true, detail: 'Fechas DD/MM/YYYY y timestamps DD/MM/YYYY, HH:mm en Lima; pruebas de utilidades independientes.' })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(base + '/clientes', { waitUntil: 'networkidle' })
  await page.getByPlaceholder('Buscar por nombre, DNI o teléfono...').fill(clients[0].document)
  const mobileDetail = page.getByRole('link', { name: 'Ver detalle de ' + business, exact: true })
  await mobileDetail.scrollIntoViewIfNeeded()
  await capture('R01-detalle-mobile.png')
  await mobileDetail.click()
  await page.waitForURL('**/clientes/' + clients[0].id)
  results.push({ card: 'R01-mobile', passed: true, detail: 'Detalle abierto en móvil sin hover, con desplazamiento horizontal de tabla.' })
} catch (error) {
  results.push({ card: 'Ejecución', passed: false, detail: error.message })
} finally {
  await browser.close()
  await writeFile(path.join(output, 'reporte-mejoras.json'), JSON.stringify({ started, finished: new Date().toISOString(), url: base, locale: 'es-PE', timezone: 'America/Lima', type: 'Prueba técnica posterior; aceptación con propietario pendiente', results }, null, 2))
  console.log(JSON.stringify({ checks: results.length, failures: results.filter(result => !result.passed) }))
  if (results.some(result => !result.passed)) process.exitCode = 1
}
