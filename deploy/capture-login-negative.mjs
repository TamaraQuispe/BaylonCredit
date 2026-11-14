// One controlled invalid attempt on the academic demo, followed by valid access.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const base = 'https://demo-credify.168-75-71-113.sslip.io'
const output = process.argv[2]
if (!output || !process.env.DEMO_USER_PASSWORD) throw Error('Output and demo password required')
await mkdir(output, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, locale: 'es-PE', timezoneId: 'America/Lima' })
page.setDefaultTimeout(30000)
const started = new Date().toISOString()
const report = { started, url: base, type: 'Prueba automatizada del equipo; no prueba de Oracle ni sesión del propietario', results: [] }
try {
  await page.goto(base + '/iniciar-sesion', { waitUntil: 'networkidle' })
  await page.locator('#email').fill('docente@example.com')
  await page.locator('#password').fill('Incorrecta-Prueba-APF2!')
  const invalidResponse = page.waitForResponse(response => response.url().endsWith('/auth/login') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  const rejected = await invalidResponse
  assert.equal(rejected.status(), 401)
  const body = await rejected.json()
  const message = String(body.detail)
  const errorBox = page.locator('form .bg-error-container')
  await errorBox.waitFor({ state: 'visible' })
  assert.ok((await errorBox.innerText()).includes(message))
  assert.ok(page.url().endsWith('/iniciar-sesion'))
  assert.equal(await page.evaluate(() => sessionStorage.getItem('credify_auth_session') || localStorage.getItem('credify_auth_session')), null)
  report.results.push({ case: 'Contraseña incorrecta en cuenta de demo', expected: 401, actual: rejected.status(), message, passed: true, session_created: false })
  await page.screenshot({ path: path.join(output, 'login-credenciales-invalidas.png'), fullPage: true })
  await page.locator('#password').fill(process.env.DEMO_USER_PASSWORD)
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  await page.waitForURL('**/inicio')
  report.results.push({ case: 'Acceso válido posterior al intento controlado', passed: true })
} catch (error) {
  report.results.push({ case: 'Ejecución', passed: false, detail: error.message })
  process.exitCode = 1
} finally {
  report.finished = new Date().toISOString()
  await browser.close()
  await writeFile(path.join(output, 'login-credenciales-invalidas.json'), JSON.stringify(report, null, 2))
  console.log(JSON.stringify({ checks: report.results.length, passed: report.results.every(result => result.passed), finished: report.finished }))
}
