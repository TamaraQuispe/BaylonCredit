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
page.setDefaultTimeout(60000)
const results = []
const started = new Date().toISOString()
let token
async function api(route, method = 'GET') {
  const response = await page.request.fetch(base + '/api/v1' + route, { method, headers: { Authorization: `Bearer ${token}` }, timeout: 60000 })
  assert.equal(response.status(), 200, route)
  return response.json()
}
try {
  const unauthorized = await page.request.get(base + '/api/v1/academic-ml/summary')
  assert.equal(unauthorized.status(), 401)
  results.push({ case: 'Laboratorio requiere autenticación', passed: true })
  await page.goto(base + '/iniciar-sesion')
  await page.locator('#email').fill('docente@example.com')
  await page.locator('#password').fill(process.env.DEMO_USER_PASSWORD)
  await page.getByRole('button', { name: 'Ingresar a Credify', exact: true }).click()
  await page.waitForURL('**/inicio')
  token = await page.evaluate(() => JSON.parse(sessionStorage.getItem('credify_auth_session') || localStorage.getItem('credify_auth_session')).accessToken)
  const before = { credits: (await api('/credits')).length, evaluations: (await api('/credits/evaluations')).length }
  await page.goto(base + '/evaluacion-crediticia', { waitUntil: 'networkidle' })
  await page.getByRole('link', { name: 'Laboratorio ML' }).click()
  await page.getByRole('heading', { name: 'Laboratorio académico ML' }).waitFor()
  await page.getByRole('heading', { name: 'Comparación en la cohorte sintética final' }).waitFor()
  results.push({ case: 'Ruta y enlace de demo funcionan; comparación visible', passed: true })
  const summary = await api('/academic-ml/summary')
  assert.equal(summary.data_source, 'synthetic')
  assert.equal(summary.version, 'academic-synthetic-late-v2')
  assert.ok(summary.comparison.second_model.accuracy < summary.comparison.majority_baseline.accuracy)
  const cases = await api('/academic-ml/cases')
  assert.ok(cases.length > 1)
  for (const item of cases) {
    const response = await api('/academic-ml/evaluate/' + item.id, 'POST')
    assert.equal(response.data_source, 'synthetic')
    assert.equal(response.case_id, item.id)
    assert.ok(response.estimated_late_probability >= 0 && response.estimated_late_probability <= 1)
    assert.equal(Object.keys(response.features).length, 11)
  }
  results.push({ case: 'Inferencia real del artefacto sobre casos predefinidos', cases: cases.length, passed: true })
  await page.getByRole('combobox', { name: 'Caso sintético' }).selectOption(cases[0].id)
  await page.getByRole('button', { name: 'Evaluar caso sintético', exact: true }).click()
  await page.getByText('Predicción del modelo', { exact: true }).waitFor()
  await page.screenshot({ path: path.join(output, 'laboratorio-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.screenshot({ path: path.join(output, 'laboratorio-mobile.png'), fullPage: true })
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false)
  results.push({ case: 'Consulta en navegador y pantalla móvil sin desborde de página', passed: true })
  const after = { credits: (await api('/credits')).length, evaluations: (await api('/credits/evaluations')).length }
  assert.deepEqual(after, before)
  results.push({ case: 'Consultas ML no agregaron créditos ni evaluaciones de fiado', passed: true })
} catch (error) {
  results.push({ case: 'Ejecución', passed: false, detail: error.message })
  process.exitCode = 1
} finally {
  await browser.close()
  const report = { started, finished: new Date().toISOString(), url: base + '/laboratorio-academico', scope: 'Prueba técnica de laboratorio sintético; no aceptación humana ni operación productiva', results }
  await writeFile(path.join(output, 'verificacion-laboratorio.json'), JSON.stringify(report, null, 2))
  console.log(JSON.stringify({ checks: results.length, failures: results.filter(result => !result.passed) }))
}
