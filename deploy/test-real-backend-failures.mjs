// Stop/pause ONLY containers whose Compose project label is credify-resilience.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { performance } from 'node:perf_hooks'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const output = process.argv[2]
if (!output) throw Error('Evidence output directory required')
await mkdir(output, { recursive: true })
const base = 'http://127.0.0.1:8093'
const project = 'credify-resilience'
const composeArgs = ['compose', '-p', project, '-f', 'docker-compose.resilience.yml']
const docker = (...args) => execFileSync('docker', args, { encoding: 'utf8', timeout: 60000 }).trim()
const compose = (...args) => docker(...composeArgs, ...args)
const containers = {}
for (const service of ['database', 'api', 'frontend']) {
  const id = compose('ps', '-q', service)
  assert.ok(id, `Missing test container ${service}`)
  assert.equal(docker('inspect', '-f', '{{index .Config.Labels "com.docker.compose.project"}}', id), project)
  containers[service] = id
}
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'es-PE', timezoneId: 'America/Lima' })
page.setDefaultTimeout(25000)
page.on('pageerror', error => console.log('Browser runtime error:', error.message))
page.on('requestfailed', request => console.log('Browser request failed:', new URL(request.url()).pathname, request.failure()?.errorText))
const started = new Date().toISOString()
const cases = []
let paused = false
let stoppedDb = false
let stoppedApi = false
const message = 'Sistema no disponible temporalmente. Inténtalo más tarde.'
let token
async function ready() {
  for (let i = 0; i < 40; i++) {
    try {
      const response = await page.request.get(base + '/health/ready', { timeout: 3000 })
      if (response.status() === 200) return
    } catch { /* test service still recovering */ }
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  throw Error('Isolated backend did not recover')
}
async function count(document) {
  assert.match(document, /^\d{8}$/)
  return Number(docker('exec', containers.database, 'psql', '-U', 'resilience', '-d', 'credify_resilience', '-tA', '-c', `SELECT count(*) FROM clients WHERE document='${document}'`))
}
async function databaseOutageHealth() {
  const live = (await page.request.get(base + '/health/live')).status()
  const ready = (await page.request.get(base + '/health/ready')).status()
  assert.equal(live, 200)
  assert.equal(ready, 503)
  return { liveness_http: live, readiness_http: ready }
}
async function draft(document) {
  await page.goto(base + '/clientes/nuevo', { waitUntil: 'networkidle' })
  await page.locator('#nombres').fill('Cliente ficticio')
  await page.locator('#apellidos').fill('Resiliencia')
  await page.locator('#documento').fill(document)
  await page.locator('#telefono').fill('000000000')
  await page.locator('#negocio').fill('TEST AISLADO - No es dato real')
  await page.getByRole('checkbox').check()
  assert.equal(await page.locator('form').evaluate(form => form.checkValidity()), true, 'Prepared test form must be valid before the outage')
}
async function failedSubmit(name, expected, document) {
  let posts = 0
  const record = request => { if (request.url().endsWith('/api/v1/clients') && request.method() === 'POST') posts++ }
  page.on('request', record)
  assert.equal(await page.locator('form').evaluate(form => form.checkValidity()), true)
  await page.evaluate(() => {
    window.__faultEvents = []
    document.querySelector('form').addEventListener('submit', () => window.__faultEvents.push('submit'))
  })
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/clients') && response.request().method() === 'POST')
  const start = performance.now()
  const [response] = await Promise.all([
    responsePromise,
    page.locator('form').evaluate(form => form.requestSubmit()),
  ])
  assert.ok(expected.includes(response.status()), `Expected HTTP ${expected.join('/')} but received ${response.status()}`)
  await page.getByText(message, { exact: true }).waitFor()
  assert.equal(await page.locator('#nombres').inputValue(), 'Cliente ficticio')
  assert.equal(await page.locator('#apellidos').inputValue(), 'Resiliencia')
  assert.equal(await page.locator('#documento').inputValue(), document)
  assert.equal(await page.locator('#telefono').inputValue(), '000000000')
  assert.equal(await page.locator('#negocio').inputValue(), 'TEST AISLADO - No es dato real')
  assert.equal(await page.getByRole('checkbox').isChecked(), true)
  assert.equal(posts, 1, 'No automatic write retry')
  assert.equal(await page.evaluate(() => JSON.parse(sessionStorage.getItem('credify_auth_session')).accessToken), token)
  const elapsedMs = Math.round(performance.now() - start)
  assert.ok(elapsedMs < 15000, 'Failure must be bounded')
  const headers = response.headers()
  if (response.status() === 503) {
    const body = await response.json()
    assert.equal(body.detail, message)
    assert.equal(body.code, 'database_unavailable')
    assert.equal(headers['retry-after'], '5')
    assert.ok(headers['x-request-id'])
    assert.doesNotMatch(JSON.stringify(body), /postgresql|isolated-test-database|SELECT /i)
  }
  await page.screenshot({ path: path.join(output, name + '.png'), fullPage: true })
  page.off('request', record)
  return { name, expected_http: expected, actual_http: response.status(), elapsed_ms: elapsedMs, form_preserved: true, automatic_retries: 0, passed: true, request_id: headers['x-request-id'] || null }
}
async function recover(name, document) {
  await ready()
  assert.equal(await count(document), 0, 'Failed request did not persist a client')
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/clients') && response.request().method() === 'POST')
  const [response] = await Promise.all([
    responsePromise,
    page.locator('form').evaluate(form => form.requestSubmit()),
  ])
  assert.equal(response.status(), 201)
  await page.waitForURL('**/clientes/*')
  assert.equal(await count(document), 1, 'Explicit retry persisted exactly one test client')
  cases.push({ name: 'Recuperación después de ' + name, passed: true, rows_before_retry: 0, rows_after_retry: 1 })
  await page.screenshot({ path: path.join(output, name + '-recuperado.png'), fullPage: true })
}
try {
  await ready()
  await page.goto(base + '/iniciar-sesion')
  await page.locator('#email').fill('fault-test@example.com')
  await page.locator('#password').fill('Resilience-Test-Only!')
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  await page.waitForURL('**/inicio')
  token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('credify_auth_session')).accessToken)
  assert.ok(token)
  const serial = String(Date.now()).slice(-6)
  const first = '81' + serial
  await draft(first)
  compose('stop', '-t', '3', 'database')
  stoppedDb = true
  const stoppedHealth = await databaseOutageHealth()
  cases.push({ ...await failedSubmit('01-postgresql-detenido', [503], first), ...stoppedHealth })
  compose('start', 'database')
  stoppedDb = false
  await recover('postgresql-detenido', first)

  const second = '82' + serial
  await draft(second)
  compose('pause', 'database')
  paused = true
  const timeoutCase = await failedSubmit('02-postgresql-timeout', [503], second)
  cases.push({ ...timeoutCase, ...await databaseOutageHealth() })
  compose('unpause', 'database')
  paused = false
  await recover('postgresql-timeout', second)

  const third = '83' + serial
  await draft(third)
  compose('stop', '-t', '3', 'api')
  stoppedApi = true
  cases.push(await failedSubmit('03-api-detenida-proxy', [502, 504], third))
  compose('start', 'api')
  stoppedApi = false
  await recover('api-detenida', third)
} catch (error) {
  cases.push({ name: 'Ejecución', passed: false, error: error.message })
  await page.screenshot({ path: path.join(output, 'diagnostico-ejecucion.png'), fullPage: true }).catch(() => {})
  console.log('Failure at isolated test page:', page.url(), error.message)
  console.log('Form submit diagnostics:', await page.evaluate(() => window.__faultEvents || []).catch(() => []))
  process.exitCode = 1
} finally {
  if (paused) compose('unpause', 'database')
  if (stoppedDb) compose('start', 'database')
  if (stoppedApi) compose('start', 'api')
  await browser.close()
  await writeFile(path.join(output, 'fallos-backend-reales.json'), JSON.stringify({ started, finished: new Date().toISOString(), scope: 'Contenedores LOCALES exclusivos credify-resilience; sin servicios públicos ni datos del negocio', source: base, database: 'PostgreSQL 17 aislado', server_timeouts_seconds: 2, proxy_connect_timeout_seconds: 3, form_submission: 'HTMLFormElement.requestSubmit; handler React real', no_browser_network_interception: true, results: cases, limits: 'No demuestra exactamente-una-vez si un commit remoto se confirmó y se perdió su respuesta; verificar historial antes de reenviar. No es validación de propietario ni caída de producción.' }, null, 2))
  console.log(JSON.stringify({ checks: cases.length, failures: cases.filter(item => !item.passed) }))
}
