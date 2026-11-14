// Capture actual demo screens and safe test results; never target production.
import { copyFile, mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const base = 'https://demo-credify.168-75-71-113.sslip.io'
const output = process.argv[2]
if (!output || !process.env.DEMO_USER_PASSWORD) throw new Error('Output directory and demo password required')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'es-PE', timezoneId: 'America/Lima' })
page.setDefaultTimeout(30000)
const results = []
const warnings = []
const screenshots = []
const started = new Date().toISOString()
let token

async function screenshot(name) {
  await page.screenshot({ path: path.join(output, name), fullPage: true })
  screenshots.push(name)
}

async function api(name, route, body, expected = 200) {
  const response = await page.request.fetch(base + '/api/v1' + route, {
    method: body === undefined ? 'GET' : 'POST',
    headers: { Authorization: `Bearer ${token}` },
    ...(body === undefined ? {} : { data: body }),
  })
  const passed = response.status() === expected
  results.push({ name, expected, actual: response.status(), passed })
  if (!passed) throw new Error(`${name}: expected ${expected}, got ${response.status()}`)
  return response.json()
}

try {
  await page.goto(base + '/iniciar-sesion', { waitUntil: 'networkidle' })
  await screenshot('01-login-desktop.png')
  const logoLoaded = await page.locator('img').evaluateAll(images => images.every(img => img.complete && img.naturalWidth > 0))
  results.push({ name: 'Logos locales del login cargan', passed: logoLoaded })
  await page.locator('#email').fill('docente@example.com')
  await page.locator('#password').fill(process.env.DEMO_USER_PASSWORD)
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  await page.waitForURL('**/inicio')
  await page.waitForLoadState('networkidle')
  results.push({ name: 'Login mediante formulario del navegador', passed: true })
  token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('credify_auth_session') || localStorage.getItem('credify_auth_session')).accessToken)
  const document = '9' + String(Date.now()).slice(-7)
  const client = await api('Registro de cliente ficticio', '/clients', {
    first_name: 'Cliente', last_name: 'Evidencia APF2', business_name: 'DEMO - Evidencia APF2 ' + document,
    document, phone: '000000000', address: 'Registro ficticio de prueba',
  }, 201)
  await page.goto(base + '/clientes', { waitUntil: 'networkidle' })
  const allClients = await api('Clientes para comprobar contador', '/clients')
  const counter = page.getByRole('button', { name: /^Todos los clientes/ })
  const counterText = await counter.innerText()
  results.push({ name: 'Contador corresponde a clientes cargados', passed: counterText.trim().endsWith(String(allClients.length)) })
  await screenshot('02-clientes-desktop.png')
  await api('Monto cero rechazado', '/credits/evaluate', { client_id: client.id, amount: '0' }, 422)
  await page.goto(base + '/evaluacion-crediticia?cliente=' + client.id, { waitUntil: 'networkidle' })
  await page.getByLabel('Monto a evaluar').fill('50')
  const evaluated = page.waitForResponse(response => response.url().endsWith('/credits/evaluate') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Evaluar crédito', exact: true }).click()
  const response = await evaluated
  const evaluation = await response.json()
  const validEvaluation = response.status() === 200 && evaluation.model_version === 'rules-v1' && evaluation.ai_status === 'disabled'
  results.push({ name: 'Evaluación por reglas mediante navegador', passed: validEvaluation })
  if (!validEvaluation) throw new Error('Unexpected demo evaluation mode')
  await page.getByRole('heading', { name: 'Condiciones recomendadas' }).waitFor()
  await page.getByRole('button', { name: 'Recalcular', exact: true }).waitFor()
  await screenshot('03-evaluacion-desktop.png')
  const desktopOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  if (desktopOverflow) warnings.push('Revisar desbordamiento horizontal en escritorio.')
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'America/Lima' })
  const credit = await api('Creación de fiado', '/credits', { client_id: client.id, amount: '50', credit_date: today }, 201)
  results.push({ name: 'Vencimiento a un día', passed: Date.parse(credit.due_date) - Date.parse(today) === 86400000 })
  await page.goto(base + '/creditos/' + credit.id, { waitUntil: 'networkidle' })
  await screenshot('04-fiado-antes-del-pago.png')
  await api('Pago excesivo rechazado', '/payments', {
    client_id: client.id, allocations: [{ credit_id: credit.id, amount: '60' }], payment_date: today, method: 'efectivo',
  }, 409)
  await api('Registro de abono parcial', '/payments', {
    client_id: client.id, allocations: [{ credit_id: credit.id, amount: '20' }], payment_date: today, method: 'efectivo', reference: 'DEMO - Evidencia APF2',
  }, 201)
  const saved = await api('Consulta posterior del crédito', '/credits/' + credit.id)
  results.push({ name: 'Saldo persistido S/ 30', passed: Number(saved.pending_amount) === 30 })
  await page.reload({ waitUntil: 'networkidle' })
  await screenshot('05-fiado-despues-del-pago.png')
  if (process.env.APF2_TASK_CAPTURES) {
    await page.goto(base + '/pagos', { waitUntil: 'networkidle' })
    await screenshot('11-pagos-desktop.png')
  }
  await page.goto(base + '/evaluacion-crediticia?cliente=' + client.id, { waitUntil: 'networkidle' })
  const history = await api('Historial de evaluaciones consultable', '/credits/evaluations?client_id=' + client.id)
  results.push({ name: 'Historial contiene evaluación', passed: history.length > 0 })
  await screenshot('06-historial-desktop.png')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(base + '/evaluacion-crediticia?cliente=' + client.id, { waitUntil: 'networkidle' })
  await screenshot('07-evaluacion-mobile.png')
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  if (overflow) warnings.push('Revisar desbordamiento horizontal en la captura mobile; no se declara validación responsive completa.')
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto(base + '/clientes/nuevo', { waitUntil: 'networkidle' })
  let attempts = 0
  const countClientPosts = request => {
    if (request.url().endsWith('/api/v1/clients') && request.method() === 'POST') attempts++
  }
  page.on('request', countClientPosts)
  await page.getByRole('button', { name: 'Guardar cliente' }).click()
  const invalid = await page.locator('#nombres').evaluate(input => input.validity.valueMissing)
  results.push({ name: 'Formulario vacío bloqueado por validación del navegador', passed: invalid && attempts === 0 })
  await screenshot('08-formulario-vacio-validacion.png')
  await page.locator('#nombres').fill('Cliente demo')
  await page.locator('#apellidos').fill('Fallo de red simulado')
  await page.locator('#documento').fill('9' + String(Date.now()).slice(-7))
  await page.locator('#telefono').fill('000000000')
  await page.getByRole('checkbox').check()
  await page.route('**/api/v1/clients', route => route.request().method() === 'POST' ? route.abort('failed') : route.continue())
  await page.getByRole('button', { name: 'Guardar cliente' }).click()
  await page.getByText(/Failed to fetch|No se pudo registrar|NetworkError/i).waitFor()
  results.push({ name: 'Error de red simulado: mensaje visible y formulario conservado', passed: await page.locator('#nombres').inputValue() === 'Cliente demo' })
  await screenshot('09-error-red-simulado.png')
  await page.unroute('**/api/v1/clients')
  page.off('request', countClientPosts)
  if (results.some(result => !result.passed)) throw new Error('At least one assertion failed')
} catch (error) {
  warnings.push(error.message)
  results.push({ name: 'Ejecución completa', passed: false })
} finally {
  await browser.close()
  const report = { started, finished: new Date().toISOString(), url: base, type: 'Prueba automatizada del equipo; no validación del propietario', results, warnings, screenshots }
  await writeFile(path.join(output, 'reporte-pruebas.json'), JSON.stringify(report, null, 2))
  await writeFile(path.join(output, 'README.md'), `# Evidencias APF2\n\nURL: ${base}\n\nInicio UTC: ${started}\n\nDatos ficticios. Pruebas del equipo, no entrevista del propietario.\n\n${results.map(result => `- ${result.passed ? 'PASÓ' : 'NO PASÓ'}: ${result.name}`).join('\n')}\n\n${warnings.map(warning => `- Observación: ${warning}`).join('\n')}\n\nCapturas:\n${screenshots.map(name => `- ${name}`).join('\n')}\n`)
  if (process.env.APF2_TASK_CAPTURES && !results.some(result => !result.passed)) {
    const tasks = process.env.APF2_TASK_CAPTURES
    await mkdir(tasks, { recursive: true })
    const mapping = {
      'T1_01_login.png': '01-login-desktop.png',
      'T2_01_clientes.png': '02-clientes-desktop.png',
      'T3_01_evaluacion.png': '03-evaluacion-desktop.png',
      'T4_01_fiado.png': '04-fiado-antes-del-pago.png',
      'T5_01_pago.png': '11-pagos-desktop.png',
      'T6_04_historiales.png': '05-fiado-despues-del-pago.png',
    }
    for (const [target, source] of Object.entries(mapping)) await copyFile(path.join(output, source), path.join(tasks, target))
    await writeFile(path.join(tasks, 'README.md'), `# Capturas T1-T6\n\nTomadas técnicamente por OpenCode en ${started} (UTC), después de la sesión declarada de Rildo. NO son capturas de esa sesión ni acreditan su participación. Datos ficticios.\n\n${Object.entries(mapping).map(([target, source]) => `- ${target}: ${source}`).join('\n')}\n`)
    await writeFile(path.join(tasks, 'procedencia.json'), JSON.stringify({ started, finished: report.finished, source: base, author: 'OpenCode, navegador automatizado', not_owner_session: true, mapping }, null, 2))
  }
  console.log(JSON.stringify({ tests: results.length, failed: results.filter(result => !result.passed).length, screenshots: screenshots.length, warnings }))
}
