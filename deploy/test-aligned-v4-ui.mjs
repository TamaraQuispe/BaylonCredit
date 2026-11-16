// Run against an already running LOCAL production preview, never a deployed site.
// BASE_URL=http://127.0.0.1:4173 PLAYWRIGHT_MODULE_PATH=/absolute/path/playwright/index.mjs node deploy/test-aligned-v4-ui.mjs
// Optional: SCREENSHOT_DIR=/temporary/output; V4_FLAG_ENABLED=false for a separately built flag-off preview.
// V2_FLAG_ENABLED=true additionally verifies that the existing V2 link remains available.
import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { setTimeout as delay } from 'node:timers/promises'
import { pathToFileURL } from 'node:url'

const base = new URL(process.env.BASE_URL || 'http://127.0.0.1:4173')
assert.ok(base.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname)
  && !base.username && !base.password && base.pathname === '/' && !base.search && !base.hash,
'BASE_URL must be a loopback HTTP origin without credentials, path or query')
const origin = base.origin
const enabled = process.env.V4_FLAG_ENABLED !== 'false'
const screenshotDirectory = process.env.SCREENSHOT_DIR
const labPath = '/laboratorio-academico/v4'
const apiPrefix = '/academic-ml/v4'
const research = {
  version: 'academic-owner-aligned-v4', data_source: 'synthetic', research_only: true, business_approval: false,
}
const metrics = (f2) => ({
  accuracy: 0.72, balanced_accuracy: 0.71, precision: 0.6, recall: 0.8,
  f1: 0.6857, f2, roc_auc: 0.76, brier: 0.18, confusion_matrix: [[30, 12], [4, 16]],
})
const summary = {
  ...research, selected_model: 'svm', threshold: 0.31,
  development_rows: 400, development_unknown: 30, development_clients: 150,
  final_labeled_rows: 62, final_unknown: 6, final_clients: 29,
  selection: { metric: 'oof_f2', oof_f2: 0.8123 },
  comparison: ['svm', 'tree', 'most_frequent', 'constant_1'].map((family, index) => ({
    family, label: ['SVM', 'Arbol', 'Clase mayoritaria', 'Siempre atraso'][index],
    raw: metrics([0.7412, 0.8321, 0, 0.7][index]),
    policy: {
      metrics: metrics([0.6123, 0.6789, 0, 0.5][index]),
      reviews: 20, reviews_known: 17, reviews_unknown: 3, daily_max: 5, capacity_respected: true,
    },
  })),
  source: {
    evaluable: 45, late: 8, partial_annotations: 10, partial_denominator: 48,
    quality: 'Recuerdo y cuaderno parcial; aproximado, no auditado.',
  },
  limitations: ['No valida poblacion real.', 'Capacidad estimada, no medida.'],
  disclaimer: 'Solo investigacion sintetica. Sin aprobacion comercial.',
}
const cases = [{ id: 'illustrative-v4', scenario: 'Ejemplo ficticio sin etiqueta', requested_amount: '20.00' }]
const evaluation = {
  ...research, case_id: 'illustrative-v4', scenario: cases[0].scenario,
  estimated_late_probability: 0.42, threshold: 0.31, predicted_late_payment: 1,
  actual_late_payment: null, features: { requested_amount: 20, history_count: 0, prior_delay: null },
  review_policy_applied: false, disclaimer: 'Score individual, sin cola ni decision comercial.',
}

let browser
let stage = 'loading Playwright'
let completed = 0
let blocked = 0
const unexpected = []
const runtimeErrors = []

async function visible(locator) {
  await locator.waitFor({ state: 'visible' })
}

async function fixture(role, viewport, state = {}, authenticated = true) {
  const context = await browser.newContext({ viewport, serviceWorkers: 'block' })
  const calls = []
  await context.addInitScript(({ role, authenticated }) => {
    localStorage.removeItem('credify_auth_session')
    sessionStorage.removeItem('credify_auth_session')
    if (authenticated) {
      const encode = (value) => btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
      const token = `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: 'v4-browser-fixture', exp: Math.floor(Date.now() / 1000) + 3600 })}.fixture`
      sessionStorage.setItem('credify_auth_session', JSON.stringify({
        accessToken: token, refreshToken: token,
        user: { id: 'v4-browser-fixture', nombre: 'Usuario Ficticio', correo: 'v4@example.invalid',
          iniciales: 'UF', rol: role, mustChangePassword: false },
      }))
    }
    // Observe AbortSignals without retaining headers, tokens, bodies or traces.
    window.__v4Requests = []
    const originalFetch = window.fetch
    window.fetch = (input, options) => {
      const pathname = new URL(typeof input === 'string' ? input : input.url, location.href).pathname
      if (pathname.includes('/academic-ml/v4/')) {
        const entry = { pathname, aborted: options?.signal?.aborted || false }
        window.__v4Requests.push(entry)
        options?.signal?.addEventListener('abort', () => { entry.aborted = true }, { once: true })
      }
      return originalFetch(input, options)
    }
    document.addEventListener('DOMContentLoaded', () => {
      const style = document.createElement('style')
      style.textContent = '.material-symbols-outlined { width: 24px; overflow: hidden; flex-shrink: 0; }'
      document.head.append(style)
    })
  }, { role, authenticated })

  // Installed before navigation: every API request is fulfilled, including remote compiled API origins.
  await context.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (/^\/api\/v1(?:\/|$)/.test(url.pathname)) {
      const pathname = url.pathname.replace(/^\/api\/v1/, '').replace(/\/$/, '')
      const method = request.method()
      const headers = {
        'access-control-allow-origin': origin,
        'access-control-allow-methods': 'GET, POST, OPTIONS',
        'access-control-allow-headers': 'authorization, content-type',
      }
      if (method === 'OPTIONS') return route.fulfill({ status: 204, headers })
      calls.push({ pathname, method, body: request.postData() })
      let json
      let status = 200
      if (method === 'GET' && pathname === `${apiPrefix}/summary`) {
        if (state.holdLoad) await state.holdLoad
        status = state.summaryError ? 503 : 200
        json = state.summaryOverride || summary
      } else if (method === 'GET' && pathname === `${apiPrefix}/cases`) {
        if (state.holdLoad) await state.holdLoad
        status = state.casesError ? 500 : 200
        json = state.casesOverride || cases
      } else if (method === 'POST' && pathname === `${apiPrefix}/evaluate/illustrative-v4`) {
        if (state.holdEvaluation) await state.holdEvaluation
        status = state.evaluationError ? 500 : 200
        json = state.evaluationOverride || evaluation
      } else if (method === 'GET' && ['/clients', '/credits', '/payments', '/products', '/sales', '/credits/evaluations'].includes(pathname)) {
        json = []
      } else if (method === 'GET' && pathname === '/settings') {
        json = { business_name: 'Fixture aislada', business_phone: '', business_address: '',
          default_credit_term_days: 15, max_credit_amount: '500', due_alerts_enabled: false }
      } else if (method === 'GET' && pathname === '/credits/evaluations/summary') {
        json = { total_clients: 0, evaluated_clients: 0, coverage_percent: 0 }
      } else {
        unexpected.push(`${method} ${pathname}`)
        json = { detail: 'Unconfigured isolated fixture' }
        status = 501
      }
      if (status !== 200 && status !== 501) json = { detail: 'Fallo simulado, reintenta manualmente.' }
      await route.fulfill({ status, headers, contentType: 'application/json', body: JSON.stringify(json) })
    } else if (url.origin === origin && !['fetch', 'xhr'].includes(request.resourceType())) {
      await route.continue()
    } else {
      blocked += 1
      await route.abort('blockedbyclient')
    }
  })
  const page = await context.newPage()
  page.setDefaultTimeout(10_000)
  page.on('pageerror', (error) => runtimeErrors.push(error.name))
  return { context, page, calls }
}

async function ready(page) {
  await visible(page.getByRole('heading', { name: 'SVM seleccionado en desarrollo', exact: true }))
}

async function navigateAway(page) {
  // A genuine client-side navigation preserves the instrumented window for abort assertions.
  await page.locator('a[href="/evaluacion-crediticia"]').first().evaluate((link) => link.click())
  await visible(page.getByRole('heading', { name: 'Evaluaci\u00f3n crediticia', exact: true }))
}

async function screenshot(page, name) {
  if (screenshotDirectory) {
    await page.evaluate(() => window.scrollTo(0, 0))
    await page.screenshot({ path: path.join(screenshotDirectory, `${name}.png`), fullPage: true })
  }
}

async function verify(role, viewport) {
  const label = `${role}-${viewport.width < 768 ? 'mobile' : 'desktop'}`
  stage = label
  const { context, page, calls } = await fixture(role, viewport)
  try {
    await page.goto(`${origin}/evaluacion-crediticia`)
    if (process.env.V2_FLAG_ENABLED === 'true') {
      await visible(page.getByRole('link', { name: 'Laboratorio ML', exact: true }))
    }
    const link = page.getByRole('link', { name: 'Laboratorio ML V4', exact: true })
    if (!enabled) {
      await visible(page.getByRole('heading', { name: 'Evaluaci\u00f3n crediticia', exact: true }))
      assert.equal(await link.count(), 0, 'flag off hides V4 link')
      await page.goto(`${origin}${labPath}`)
      await page.waitForURL(`${origin}/inicio`)
      assert.equal(await page.getByRole('heading', { name: 'Laboratorio acad\u00e9mico ML V4', exact: true }).count(), 0)
      assert.equal(calls.filter((call) => call.pathname.startsWith(apiPrefix)).length, 0, 'flag off never calls V4')
    } else {
      await link.click()
      await ready(page)
      const select = page.getByRole('combobox', { name: 'Caso ficticio', exact: true })
      const evaluate = page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true })
      assert.equal(await evaluate.isDisabled(), true, 'must explicitly select the fixture')
      assert.equal(await page.locator('main input, main textarea').count(), 0, 'no free data input')
      assert.deepEqual(await select.locator('option').evaluateAll((options) => options.map((option) => option.value)), ['', 'illustrative-v4'])
      assert.equal(await page.getByText('Variables sint\u00e9ticas utilizadas', { exact: true }).count(), 0, 'features not invented before evaluation')
      for (const [name, values] of [
        ['Raw: sin pol\u00edtica de revisi\u00f3n', [0.7412, 0.8321, 0, 0.7]],
        ['Pol\u00edtica top-5: m\u00e9tricas precalculadas', [0.6123, 0.6789, 0, 0.5]],
      ]) {
        const table = page.getByRole('table', { name, exact: true })
        assert.equal(await table.getByRole('columnheader').count(), 5, 'all four families shown')
        assert.deepEqual(await table.getByRole('row', { name: /^F2 / }).getByRole('cell').allTextContents(),
          values.map((value) => value.toLocaleString('es-PE', { maximumFractionDigits: 4 })), 'F2 raw and policy must not be swapped')
      }
      await visible(page.getByText('8/45', { exact: true }))
      await visible(page.getByText('10/48', { exact: true }))
      await visible(page.getByText(summary.source.quality, { exact: false }))
      await visible(page.getByText(summary.limitations[0], { exact: true }))
      const mainText = await page.locator('main').innerText()
      assert.match(mainText, /OOF/)
      assert.match(mainText, /ese conjunto no se usa para volver a seleccionar/)
      assert.match(mainText, /mundos sint\u00e9ticos separados/)
      await select.selectOption('illustrative-v4')
      await evaluate.click()
      await visible(page.getByText('Desenlace desconocido', { exact: true }))
      await visible(page.getByText('Candidato a revisi\u00f3n por umbral', { exact: true }))
      await page.getByText('Variables sint\u00e9ticas utilizadas', { exact: true }).click()
      await visible(page.getByText('prior_delay', { exact: true }))
      await visible(page.getByText('No disponible', { exact: true }))
      assert.doesNotMatch(await page.locator('main').innerText(), /No atraso|No hubo atraso|Sin atraso estimado/i)
      const posts = calls.filter((call) => call.method === 'POST')
      assert.deepEqual(posts, [{ pathname: `${apiPrefix}/evaluate/illustrative-v4`, method: 'POST', body: null }], 'one bodyless fictional evaluation only')
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/summary`).length, 1)
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/cases`).length, 1)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'no horizontal page overflow')
      const tableRegion = page.getByRole('region', { name: 'Raw: sin pol\u00edtica de revisi\u00f3n', exact: true })
      await tableRegion.focus()
      assert.equal(await tableRegion.evaluate((element) => element === document.activeElement), true, 'table is keyboard-focusable')
      await screenshot(page, label)
    }
    completed += 1
    console.log(`PASS ${label}: ${enabled ? 'summary, four-family raw/policy F2, bodyless evaluation, unknown outcome, mobile/keyboard layout' : 'flag-off route/link/API gates'}`)
  } finally {
    await context.close()
  }
}

async function edgeCases() {
  const viewport = { width: 1440, height: 1000 }
  stage = 'manual retry: summary and cases failures'
  for (const failure of ['summaryError', 'casesError']) {
    const state = { [failure]: true }
    const { context, page, calls } = await fixture('admin', viewport, state)
    try {
      await page.goto(`${origin}${labPath}`)
      await visible(page.getByRole('alert'))
      const count = calls.length
      await delay(200)
      assert.equal(calls.length, count, 'load errors do not auto-retry')
      state[failure] = false
      await page.getByRole('button', { name: 'Reintentar carga', exact: true }).click()
      await ready(page)
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/summary`).length, 2)
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/cases`).length, 2)
    } finally { await context.close() }
  }
  console.log('PASS summary/cases errors: manual retry only')

  stage = 'case and research-contract safety guards'
  for (const state of [
    { casesOverride: [{ ...cases[0], id: 'final-test-row' }] },
    { casesOverride: [{ ...cases[0], requested_amount: '200.00' }] },
    { casesOverride: [cases[0], cases[0]] },
    { summaryOverride: { ...summary, data_source: 'real' } },
    { summaryOverride: { ...summary, business_approval: true } },
  ]) {
    const { context, page, calls } = await fixture('admin', viewport, state)
    try {
      await page.goto(`${origin}${labPath}`)
      await visible(page.getByRole('alert'))
      assert.equal(await page.getByRole('combobox').count(), 0, 'unsafe payload never exposes a case selector')
      assert.equal(calls.filter((call) => call.method === 'POST').length, 0)
    } finally { await context.close() }
  }
  {
    const { context, page } = await fixture('admin', viewport, { casesOverride: [] })
    try {
      await page.goto(`${origin}${labPath}`)
      await ready(page)
      assert.equal(await page.getByRole('combobox').isDisabled(), true)
      assert.equal(await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).isDisabled(), true)
    } finally { await context.close() }
  }
  console.log('PASS rejects non-illustrative/multiple/modified cases and non-research summaries; empty cases disabled')

  stage = 'evaluation retry, double click, case-change abort, unmount abort, stale response'
  const state = { evaluationError: true }
  const { context, page, calls } = await fixture('admin', viewport, state)
  let release
  try {
    await page.goto(`${origin}${labPath}`)
    await ready(page)
    const select = page.getByRole('combobox', { name: 'Caso ficticio', exact: true })
    await select.selectOption('illustrative-v4')
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByRole('alert'))
    await delay(200)
    assert.equal(calls.filter((call) => call.method === 'POST').length, 1, 'no automatic POST retry')
    state.evaluationError = false
    state.holdEvaluation = new Promise((resolve) => { release = resolve })
    await page.getByRole('button', { name: 'Reintentar evaluaci\u00f3n', exact: true }).evaluate((button) => { button.click(); button.click() })
    await visible(page.getByRole('button', { name: 'Evaluando...', exact: true }))
    await page.waitForFunction(() => window.__v4Requests.filter((entry) => entry.pathname.includes('/evaluate/')).length === 2)
    await delay(100)
    assert.equal(calls.filter((call) => call.method === 'POST').length, 2, 'double click sends one additional POST')
    await select.selectOption('')
    await page.waitForFunction(() => window.__v4Requests.filter((entry) => entry.pathname.includes('/evaluate/'))[1].aborted)
    release()
    delete state.holdEvaluation
    await delay(100)
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'late response cannot display after case change')
    state.evaluationOverride = { ...evaluation, predicted_late_payment: 0, estimated_late_probability: 0.1 }
    await select.selectOption('illustrative-v4')
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByText('Por debajo del umbral de revisi\u00f3n', { exact: true }))
    await visible(page.getByText('Desenlace desconocido', { exact: true }))
    assert.doesNotMatch(await page.locator('main').innerText(), /No atraso|No hubo atraso|Sin atraso estimado/i)
    await select.selectOption('')
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'selection clears previous result')
    await select.selectOption('illustrative-v4')
    state.evaluationOverride = { ...evaluation, actual_late_payment: 0 }
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByRole('alert'))
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'reject unexpected known outcome')
    state.evaluationOverride = { ...evaluation, case_id: 'another-case' }
    await page.getByRole('button', { name: 'Reintentar evaluaci\u00f3n', exact: true }).click()
    await visible(page.getByRole('alert'))
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'reject mismatched case response')
    delete state.evaluationOverride
    state.holdEvaluation = new Promise((resolve) => { release = resolve })
    const before = calls.filter((call) => call.method === 'POST').length
    await page.getByRole('button', { name: 'Reintentar evaluaci\u00f3n', exact: true }).click()
    await page.waitForFunction((count) => window.__v4Requests.filter((entry) => entry.pathname.includes('/evaluate/')).length === count, before + 1)
    await navigateAway(page)
    assert.equal(await page.evaluate(() => window.__v4Requests.filter((entry) => entry.pathname.includes('/evaluate/')).at(-1).aborted), true, 'unmount aborts POST')
    release()
    delete state.holdEvaluation
    await page.getByRole('link', { name: 'Laboratorio ML V4', exact: true }).click()
    await ready(page)
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'no stale result after remount')
  } finally {
    release?.()
    await context.close()
  }
  console.log('PASS evaluation: manual retry, no double POST, case-change/unmount abort, stale/mismatched/known outcomes rejected, class 0 remains unknown')

  stage = 'summary and cases abort on unmount'
  let releaseLoad
  const loadState = { holdLoad: new Promise((resolve) => { releaseLoad = resolve }) }
  const loadingFixture = await fixture('admin', viewport, loadState)
  try {
    await loadingFixture.page.goto(`${origin}${labPath}`)
    await visible(loadingFixture.page.getByRole('status'))
    await loadingFixture.page.waitForFunction(() => window.__v4Requests.length === 2)
    await navigateAway(loadingFixture.page)
    assert.equal(await loadingFixture.page.evaluate(() => window.__v4Requests.every((entry) => entry.aborted)), true)
    releaseLoad()
    await delay(100)
    assert.equal(await loadingFixture.page.getByRole('heading', { name: 'SVM seleccionado en desarrollo', exact: true }).count(), 0)
  } finally {
    releaseLoad()
    await loadingFixture.context.close()
  }
  console.log('PASS summary/cases loading and abort-on-unmount')
}

try {
  const modulePath = process.env.PLAYWRIGHT_MODULE_PATH || 'playwright'
  const { chromium } = await import(path.isAbsolute(modulePath) ? pathToFileURL(modulePath).href : modulePath)
  browser = await chromium.launch({ headless: true })
  if (screenshotDirectory) await mkdir(screenshotDirectory, { recursive: true })
  for (const role of ['admin', 'operator', 'viewer']) {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) await verify(role, viewport)
  }
  if (enabled) {
    await edgeCases()
    stage = 'unauthenticated route guard'
    const { context, page, calls } = await fixture('viewer', { width: 390, height: 844 }, {}, false)
    try {
      await page.goto(`${origin}${labPath}`)
      await page.waitForURL(`${origin}/iniciar-sesion`)
      assert.equal(calls.filter((call) => call.pathname.startsWith(apiPrefix)).length, 0, 'no V4 access before authentication')
    } finally { await context.close() }
    console.log('PASS unauthenticated V4 redirects to login without V4 API calls')
  }
  stage = 'final isolation checks'
  assert.deepEqual(unexpected, [], 'no unexpected API routes or mutations')
  assert.deepEqual(runtimeErrors, [], 'no browser runtime exceptions')
  console.log(`PASS ${completed}/6 role/viewport scenarios; flag ${enabled ? 'on' : 'off'}; all API traffic mocked; ${blocked} external requests blocked; no deployment`)
  if (screenshotDirectory && enabled) console.log(`Screenshots: ${screenshotDirectory}`)
} catch (error) {
  // Never print request headers, credentials, browser storage or traces.
  console.error(`FAIL ${stage}: ${error instanceof assert.AssertionError ? error.message : error.code === 'ERR_MODULE_NOT_FOUND' ? 'Playwright module missing: set PLAYWRIGHT_MODULE_PATH' : 'browser verification failed'}`)
  process.exitCode = 1
} finally {
  if (browser) await browser.close()
}
