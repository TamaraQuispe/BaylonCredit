// Run against an already running LOCAL production preview, never a deployed site.
// BASE_URL=http://127.0.0.1:4173 PLAYWRIGHT_MODULE_PATH=/absolute/path/playwright/index.mjs node deploy/test-aligned-v6-ui.mjs
// Optional: SCREENSHOT_DIR=/temporary/output; V6_FLAG_ENABLED=false for a separately built flag-off preview.
// V4_FLAG_ENABLED=true additionally verifies that the existing V4 link remains available.
// The mock fixture mirrors the frozen academic-owner-pending-v6 bundle semantics
// (selection, counts, sources, raw/policy metrics) and never calls a real API or trains anything.
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
const enabled = process.env.V6_FLAG_ENABLED !== 'false'
const historical = process.env.V6_REVISION === 'historical'
const screenshotDirectory = process.env.SCREENSHOT_DIR
const labPath = '/laboratorio-academico/v6'
const apiPrefix = '/academic-ml/v6'
const research = {
  version: 'academic-owner-pending-v6', data_source: 'synthetic', research_only: true, business_approval: false,
}
const SELECTION_METRIC = 'OOF F2 of held-out capped review actions on known labels, beta=2'
const DISCLAIMER = 'Datos sinteticos, solo investigacion. Probabilidad experimental sin calibracion validada '
  + 'para clientes reales; no constituye aprobacion de credito ni modifica scores, creditos o notificaciones. '
  + 'Umbral individual, no cola de revision diaria con capacidad limitada. Se aplica elegibilidad previa al modelo, '
  + 'no la politica de cola diaria. La decision final corresponde a revision humana.'
const LIMITS = [
  'Synthetic histories, 24 DEV example clients and repeated observations, not real validation',
  'Owner review covers an intentional V5 sample, not all V6 rows',
  '75/25 amount mixture, exact payment-time distribution, 20:00 strict cutoff, latent Beta, warmup and stationarity are team assumptions',
  'Finite complete-payment plans do not estimate permanent loss',
  'Only linked credit sales are modeled; cash sales are unmeasured',
  'Granted-only analysis cannot estimate outcomes of rejected applications',
  'Fold-specific OOF queues miss cross-fold capacity competition and are not a deployed full-day queue',
  'Global source coherence, client consent, human review, real costs and public deployment are not certified',
  'OOF is reused for configuration and threshold selection, so winning OOF metrics are optimistic. Inner sigmoid calibration is not nested independent hyperparameter evaluation.',
  'Undefined precision uses zero_division=0',
]
const RAW = {
  svm: { accuracy: 0.6630434782608695, balanced_accuracy: 0.7169846614291058, precision: 0.23214285714285715, recall: 0.7878787878787878, f1: 0.3586206896551724, f2: 0.5327868852459017, roc_auc: 0.7156752712308269, brier: 0.10140955174449524, confusion_matrix: [[157, 86], [7, 26]] },
  tree: { accuracy: 0.39855072463768115, balanced_accuracy: 0.6060606060606061, precision: 0.1518324607329843, recall: 0.8787878787878788, f1: 0.25892857142857145, f2: 0.44891640866873067, roc_auc: 0.7079436338695598, brier: 0.19995084582132808, confusion_matrix: [[81, 162], [4, 29]] },
  most_frequent: { accuracy: 0.8804347826086957, balanced_accuracy: 0.5, precision: 0, recall: 0, f1: 0, f2: 0, roc_auc: 0.5, brier: 0.11956521739130435, confusion_matrix: [[243, 0], [33, 0]] },
  constant_1: { accuracy: 0.11956521739130435, balanced_accuracy: 0.5, precision: 0.11956521739130435, recall: 1, f1: 0.21359223300970873, f2: 0.40441176470588236, roc_auc: 0.5, brier: 0.8804347826086957, confusion_matrix: [[0, 243], [0, 33]] },
}
// The service emits policy metrics without balanced_accuracy/roc_auc/brier; they must stay null, never invented.
const POLICY = {
  svm: { accuracy: 0.6630434782608695, balanced_accuracy: null, precision: 0.23214285714285715, recall: 0.7878787878787878, f1: 0.3586206896551724, f2: 0.5327868852459017, roc_auc: null, brier: null, confusion_matrix: [[157, 86], [7, 26]] },
  tree: { accuracy: 0.39855072463768115, balanced_accuracy: null, precision: 0.1518324607329843, recall: 0.8787878787878788, f1: 0.25892857142857145, f2: 0.44891640866873067, roc_auc: null, brier: null, confusion_matrix: [[81, 162], [4, 29]] },
  most_frequent: { accuracy: 0.8804347826086957, balanced_accuracy: null, precision: 0, recall: 0, f1: 0, f2: 0, roc_auc: null, brier: null, confusion_matrix: [[243, 0], [33, 0]] },
  constant_1: { accuracy: 0.13043478260869565, balanced_accuracy: null, precision: 0.12087912087912088, recall: 1, f1: 0.21568627450980393, f2: 0.4074074074074074, roc_auc: null, brier: null, confusion_matrix: [[3, 240], [0, 33]] },
}
const POLICY_COUNTS = {
  svm: { reviews: 115, reviews_known: 112, reviews_unknown: 3, daily_max: 4, capacity_respected: true },
  tree: { reviews: 193, reviews_known: 191, reviews_unknown: 2, daily_max: 5, capacity_respected: true },
  most_frequent: { reviews: 0, reviews_known: 0, reviews_unknown: 0, daily_max: 0, capacity_respected: true },
  constant_1: { reviews: 277, reviews_known: 273, reviews_unknown: 4, daily_max: 5, capacity_respected: true },
}
const LABELS = { svm: 'SVM', tree: 'Arbol de decision', most_frequent: 'Dummy mayoritario', constant_1: 'Dummy siempre positivo' }
if (!historical) {
  Object.assign(RAW, {
    svm: { accuracy: 0.72, balanced_accuracy: 0.7449447571398791, precision: 0.32, recall: 0.7804878048780488, f1: 0.45390070921985815, f2: 0.6060606060606061, roc_auc: 0.818323952470294, brier: 0.08548605838513447, confusion_matrix: [[166, 68], [9, 32]] },
    tree: { accuracy: 0.7963636363636364, balanced_accuracy: 0.7797581821972066, precision: 0.4025974025974026, recall: 0.7560975609756098, f1: 0.5254237288135594, f2: 0.6431535269709544, roc_auc: 0.7879924953095685, brier: 0.1143837445960968, confusion_matrix: [[188, 46], [10, 31]] },
    most_frequent: { accuracy: 0.850909090909091, balanced_accuracy: 0.5, precision: 0, recall: 0, f1: 0, f2: 0, roc_auc: 0.5, brier: 0.14909090909090908, confusion_matrix: [[234, 0], [41, 0]] },
    constant_1: { accuracy: 0.14909090909090908, balanced_accuracy: 0.5, precision: 0.14909090909090908, recall: 1, f1: 0.25949367088607594, f2: 0.46697038724373574, roc_auc: 0.5, brier: 0.850909090909091, confusion_matrix: [[0, 234], [0, 41]] },
  })
  for (const family of Object.keys(RAW)) POLICY[family] = { ...RAW[family], balanced_accuracy: null, roc_auc: null, brier: null }
  Object.assign(POLICY.constant_1, { accuracy: 0.16, precision: 0.15073529411764705, f1: 0.26198083067092653, f2: 0.4701834862385321, confusion_matrix: [[3, 231], [0, 41]] })
  for (const [family, reviews, known, daily] of [['svm', 100, 100, 3], ['tree', 77, 77, 3], ['most_frequent', 0, 0, 0], ['constant_1', 274, 272, 5]]) {
    POLICY_COUNTS[family] = { reviews, reviews_known: known, reviews_unknown: reviews - known, daily_max: daily, capacity_respected: true }
  }
}
const comparison = ['svm', 'tree', 'most_frequent', 'constant_1'].map((family) => ({
  family, label: LABELS[family], raw: RAW[family], policy: { metrics: POLICY[family], ...POLICY_COUNTS[family] },
}))
const summary = {
  revision_id: 'v6-historical', display_name: 'V6 historico', training_scope: 'historical_granted_known', routing: null,
  ...research, selected_model: 'tree', threshold: 0.2,
  development_rows: 545, development_unknown: 4, development_clients: 24,
  final_labeled_rows: 276, final_unknown: 4, final_clients: 12,
  selection: { metric: SELECTION_METRIC, oof_f2: 0.5975794251134644 },
  comparison,
  source: {
    evaluable: 45, late: 8, partial_annotations: 10, partial_denominator: 48,
    quality: 'Recall and partial notebook review, approximate and not independently audited',
  },
  limitations: LIMITS,
  disclaimer: DISCLAIMER,
}
if (!historical) Object.assign(summary, {
  revision_id: 'v6-final-r1', display_name: 'V6 Final', selected_model: 'svm', threshold: 0.1,
  training_scope: 'eligible_known_only',
  development_rows: 541, development_unknown: 7, final_labeled_rows: 275, final_unknown: 2,
  selection: { metric: SELECTION_METRIC, oof_f2: 0.5523672883787661 },
  routing: {
    development: { study_attempts: 586, blocked_pending_balance: 45, requires_owner_review: 0, model_eligible: 541, simulator_refused_model_eligible: 0 },
    final: { study_attempts: 292, blocked_pending_balance: 15, requires_owner_review: 0, model_eligible: 277, simulator_refused_model_eligible: 0 },
  },
})
const cases = [
  { id: 'illustrative-v6', scenario: 'Ejemplo nuevo sin etiqueta', requested_amount: '20.00' },
  { id: 'pending-balance-v6', scenario: 'Ejemplo ficticio con saldo pendiente', requested_amount: '20.00' },
  { id: 'no-history-v6', scenario: 'Ejemplo ficticio sin creditos pagados', requested_amount: '20.00' },
]
const evaluation = {
  ...research, case_id: 'illustrative-v6', scenario: cases[0].scenario,
  estimated_late_probability: historical ? 0.7171978005286032 : 0.15310676521820216, threshold: summary.threshold, predicted_late_payment: 1,
  actual_late_payment: null,
  decision: 'model_review_candidate', model_called: true, requires_manual_review: true,
  reason: 'Estimacion experimental para revision humana, no aprobacion de credito. '
    + 'Se aplica el umbral individual, no la capacidad de la cola diaria.',
  features: {
    completed_sales: 6, paid_credits: 6, paid_late: 1, pending_overdue: 0, pending_current: 0,
    outstanding: 0, utilization: 0, requested_ratio: 0.25, tenure_days: null,
    punctuality_rate: 0.8333333333333334, overdue_rate: 0,
  },
  review_policy_applied: false, disclaimer: DISCLAIMER,
}
const evaluations = {
  'illustrative-v6': evaluation,
  'pending-balance-v6': {
    ...evaluation, case_id: cases[1].id, scenario: cases[1].scenario,
    estimated_late_probability: null, threshold: null, predicted_late_payment: null,
    decision: 'blocked_pending_balance', model_called: false, requires_manual_review: false,
    reason: 'Existe saldo pendiente actual o vencido, incluso parcial; no se evalua un nuevo credito.',
    features: { ...evaluation.features, pending_current: 1, outstanding: 20, utilization: 0.25 },
  },
  'no-history-v6': {
    ...evaluation, case_id: cases[2].id, scenario: cases[2].scenario,
    estimated_late_probability: null, threshold: null, predicted_late_payment: null,
    decision: 'requires_owner_review', model_called: false, requires_manual_review: true,
    reason: 'No hay creditos totalmente pagados confirmados; requiere revision del propietario.',
    features: { ...evaluation.features, completed_sales: 0, paid_credits: 0, paid_late: 0,
      punctuality_rate: 0, tenure_days: 0 },
  },
}

// Semantic contract of the web bundle as enforced by app.services.academic_lab_v6 (no inference, no IO).
function assertMetric(value, policy) {
  for (const name of ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'f2', 'roc_auc', 'brier']) {
    const item = value[name]
    if (policy && ['balanced_accuracy', 'roc_auc', 'brier'].includes(name)) {
      assert.ok(item === null || (Number.isFinite(item) && item >= 0 && item <= 1), `policy ${name} must be null or finite`)
    } else {
      assert.ok(Number.isFinite(item) && item >= 0 && item <= 1, `${name} must be finite in [0, 1]`)
    }
  }
  assert.equal(value.confusion_matrix.length, 2)
  for (const row of value.confusion_matrix) {
    assert.equal(row.length, 2)
    assert.ok(row.every((cell) => Number.isInteger(cell) && cell >= 0))
  }
}

function assertContract(value) {
  assert.deepEqual(
    { version: value.version, data_source: value.data_source, research_only: value.research_only, business_approval: value.business_approval },
    research, 'research-only synthetic contract')
  assert.equal(value.selected_model, historical ? 'tree' : 'svm')
  assert.equal(value.threshold, historical ? 0.2 : 0.1)
  assert.deepEqual(
    [value.development_rows, value.development_unknown, value.development_clients,
      value.final_labeled_rows, value.final_unknown, value.final_clients],
    historical ? [545, 4, 24, 276, 4, 12] : [541, 7, 24, 275, 2, 12])
  assert.equal(value.selection.metric, SELECTION_METRIC)
  assert.ok(Number.isFinite(value.selection.oof_f2))
  assert.deepEqual(value.comparison.map((model) => model.family), ['svm', 'tree', 'most_frequent', 'constant_1'])
  for (const model of value.comparison) {
    assertMetric(model.raw, false)
    assertMetric(model.policy.metrics, true)
    assert.ok(Number.isInteger(model.policy.reviews) && model.policy.reviews >= 0)
    assert.equal(model.policy.reviews_known + model.policy.reviews_unknown, model.policy.reviews)
    assert.ok(Number.isInteger(model.policy.daily_max) && model.policy.daily_max >= 0)
    assert.equal(typeof model.policy.capacity_respected, 'boolean')
  }
  assert.deepEqual(
    { evaluable: value.source.evaluable, late: value.source.late,
      partial_annotations: value.source.partial_annotations, partial_denominator: value.source.partial_denominator },
    { evaluable: 45, late: 8, partial_annotations: 10, partial_denominator: 48 })
  assert.ok(typeof value.source.quality === 'string' && value.source.quality.length > 0)
  assert.ok(Array.isArray(value.limitations) && value.limitations.length > 0)
  assert.equal(typeof value.disclaimer, 'string')
  assert.equal(value.disclaimer, DISCLAIMER)
}
assertContract(summary)
assert.deepEqual(cases.map((item) => [item.id, item.requested_amount]), [
  ['illustrative-v6', '20.00'], ['pending-balance-v6', '20.00'], ['no-history-v6', '20.00'],
])
for (const item of cases) {
  const result = evaluations[item.id]
  for (const [key, value] of Object.entries(research)) assert.equal(result[key], value)
  assert.equal(result.case_id, item.id)
  assert.equal(result.scenario, item.scenario)
  assert.equal(result.actual_late_payment, null)
  assert.equal(result.review_policy_applied, false)
  assert.equal(result.disclaimer, DISCLAIMER)
  assert.ok(result.reason.trim())
  assert.equal(result.model_called, item.id === 'illustrative-v6')
  assert.equal(result.requires_manual_review, item.id !== 'pending-balance-v6')
  assert.deepEqual([result.estimated_late_probability, result.threshold, result.predicted_late_payment],
     result.model_called ? [evaluation.estimated_late_probability, summary.threshold, 1] : [null, null, null])
  assert.equal(result.decision, item.id === 'illustrative-v6' ? 'model_review_candidate'
    : item.id === 'pending-balance-v6' ? 'blocked_pending_balance' : 'requires_owner_review')
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
      const token = `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: 'v6-browser-fixture', exp: Math.floor(Date.now() / 1000) + 3600 })}.fixture`
      sessionStorage.setItem('credify_auth_session', JSON.stringify({
        accessToken: token, refreshToken: token,
        user: { id: 'v6-browser-fixture', nombre: 'Usuario Ficticio', correo: 'v6@example.invalid',
          iniciales: 'UF', rol: role, mustChangePassword: false },
      }))
    }
    // Observe AbortSignals without retaining headers, tokens, bodies or traces.
    window.__v6Requests = []
    const originalFetch = window.fetch
    window.fetch = (input, options) => {
      const pathname = new URL(typeof input === 'string' ? input : input.url, location.href).pathname
      if (pathname.includes('/academic-ml/v6/')) {
        const entry = { pathname, aborted: options?.signal?.aborted || false }
        window.__v6Requests.push(entry)
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
      assert.equal(url.search, '', 'API requests never accept arbitrary query input')
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
      } else if (method === 'POST' && cases.some((item) => pathname === `${apiPrefix}/evaluate/${item.id}`)) {
        assert.equal(request.postData(), null, 'closed cases accept no arbitrary body')
        if (state.holdEvaluation) await state.holdEvaluation
        status = state.evaluationError ? 500 : 200
        json = state.evaluationOverride || evaluations[pathname.split('/').at(-1)]
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
  await visible(page.getByRole('heading', { name: /seleccionado en desarrollo/ }))
}

async function navigateAway(page) {
  // A genuine client-side navigation preserves the instrumented window for abort assertions.
  await page.locator('a[href="/evaluacion-crediticia"]').first().evaluate((link) => link.click())
  await visible(page.getByRole('heading', { name: 'Evaluación crediticia', exact: true }))
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
    if (process.env.V4_FLAG_ENABLED === 'true') {
      await visible(page.getByRole('link', { name: 'Laboratorio ML V4', exact: true }))
    }
    const link = page.getByRole('link', { name: 'Laboratorio ML V6 - investigación', exact: true })
    if (!enabled) {
      await visible(page.getByRole('heading', { name: 'Evaluación crediticia', exact: true }))
      assert.equal(await link.count(), 0, 'flag off hides V6 link')
      await page.goto(`${origin}${labPath}`)
      await page.waitForURL(`${origin}/inicio`)
      assert.equal(await page.getByRole('heading', { name: 'Laboratorio académico ML V6', exact: true }).count(), 0)
      assert.equal(calls.filter((call) => call.pathname.startsWith(apiPrefix)).length, 0, 'flag off never calls V6')
    } else {
      await link.click()
      await ready(page)
      const select = page.getByRole('combobox', { name: 'Caso ficticio', exact: true })
      const evaluate = page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true })
      assert.equal(await evaluate.isDisabled(), true, 'must explicitly select the fixture')
      assert.equal(await page.locator('main input, main textarea').count(), 0, 'no free data input')
      assert.deepEqual(await select.locator('option').evaluateAll((options) => options.map((option) => option.value)), ['', ...cases.map((item) => item.id)])
      assert.equal(await page.getByText('Variables sintéticas utilizadas', { exact: true }).count(), 0, 'features not invented before evaluation')
      for (const [name, values] of [
        ['Raw: sin política de revisión', comparison.map((model) => model.raw.f2)],
        ['Política con tope diario: métricas precalculadas', comparison.map((model) => model.policy.metrics.f2)],
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
      assert.match(mainText, /no se usa para volver a seleccionar/)
      assert.match(mainText, /mundos sintéticos separados/)
      assert.match(mainText, /saldo pendiente/)
      assert.match(mainText, /23 elementos/)
      assert.ok(mainText.includes(summary.display_name) && mainText.includes(summary.revision_id))
      if (!historical) {
        assert.match(mainText, /V6 Final: SVM seleccionado/)
        assert.match(mainText, /277 elegibles/)
        assert.match(mainText, /condicionales a elegibilidad/)
        assert.match(mainText, /warmup/)
        assert.doesNotMatch(mainText, /profundidad 4|0\.5965|0\.533|0\.449|545 filas/)
      }
      await select.selectOption('illustrative-v6')
      await evaluate.click()
      await visible(page.getByText('Desenlace desconocido', { exact: true }))
      await visible(page.getByText('Candidato a revisión por umbral', { exact: true }))
      await visible(page.getByText(evaluation.estimated_late_probability.toLocaleString('es-PE', { style: 'percent', maximumFractionDigits: 1 }), { exact: true }))
      const details = page.locator('details')
      await details.getByText('Variables sintéticas utilizadas', { exact: true }).click()
      await visible(details.getByText('punctuality_rate', { exact: true }))
      assert.equal(await details.getByText('No disponible', { exact: true }).count(), 1, 'null feature renders as No disponible')
      assert.doesNotMatch(await page.locator('main').innerText(), /No atraso|No hubo atraso|Sin atraso estimado/i)
      const posts = calls.filter((call) => call.method === 'POST')
      assert.deepEqual(posts, [{ pathname: `${apiPrefix}/evaluate/illustrative-v6`, method: 'POST', body: null }], 'one bodyless fictional evaluation only')
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/summary`).length, 1)
      assert.equal(calls.filter((call) => call.pathname === `${apiPrefix}/cases`).length, 1)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'no horizontal page overflow')
      const tableRegion = page.getByRole('region', { name: 'Raw: sin política de revisión', exact: true })
      await tableRegion.focus()
      assert.equal(await tableRegion.evaluate((element) => element === document.activeElement), true, 'table is keyboard-focusable')
      await screenshot(page, label)
      for (const item of cases.slice(1)) {
        await select.selectOption(item.id)
        assert.equal(await page.locator('details').count(), 0, 'case change clears eligible result')
        await evaluate.click()
        await visible(page.getByText(item.id === 'pending-balance-v6'
          ? 'Solicitud bloqueada por saldo pendiente' : 'Revisión obligatoria del propietario', { exact: true }))
        await visible(page.getByText(evaluations[item.id].reason, { exact: true }))
        await visible(page.getByText(/Modelo no ejecutado\. No se calculan probabilidad, puntaje ni predicción\./))
        for (const text of ['Probabilidad estimada de atraso', 'Señal individual del modelo',
          'Candidato a revisión por umbral', 'Por debajo del umbral de revisión', 'Desenlace desconocido']) {
          assert.equal(await page.getByText(text, { exact: true }).count(), 0, `${item.id} has no model signal`)
        }
        await page.locator('details summary').click()
        await visible(page.locator('details').getByText('paid_credits', { exact: true }))
        assert.equal(await page.locator('main input, main textarea, main [contenteditable="true"]').count(), 0)
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, `${item.id}: no page overflow`)
        await screenshot(page, `${label}-${item.id}`)
      }
      assert.deepEqual(calls.filter((call) => call.method === 'POST'), cases.map((item) => ({
        pathname: `${apiPrefix}/evaluate/${item.id}`, method: 'POST', body: null,
      })), 'exactly three closed bodyless evaluations')
    }
    completed += 1
    console.log(`PASS ${label}: ${enabled ? 'summary, four-family raw/policy F2, three closed cases, debt/history gates without signals, frozen eligible score, no overflow/free input' : 'flag-off route/link/API gates'}`)
  } finally {
    await context.close()
  }
}

async function edgeCases() {
  const viewport = { width: 1440, height: 1000 }
  stage = 'declared model families, thresholds and undefined AUC'
  for (const family of ['tree', 'svm']) {
    const alternative = { ...summary, selected_model: family, threshold: 0.35,
      comparison: summary.comparison.map((model) => model.family === family ? {
        ...model, raw: { ...model.raw, roc_auc: null, confusion_matrix: [[275, 0], [0, 0]] },
      } : model) }
    const { context, page } = await fixture('admin', viewport, {
      summaryOverride: alternative,
      evaluationOverride: { ...evaluation, threshold: 0.35, estimated_late_probability: 0.4 },
    })
    try {
      await page.goto(`${origin}${labPath}`)
      await ready(page)
      const table = page.getByRole('table', { name: 'Raw: sin política de revisión', exact: true })
      assert.ok((await table.getByRole('row', { name: /^ROC AUC / }).innerText()).includes('No disponible'))
      await page.getByRole('combobox').selectOption('illustrative-v6')
      await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
      await visible(page.getByText('Candidato a revisión por umbral', { exact: true }))
      assert.equal(await page.getByRole('alert').count(), 0)
    } finally { await context.close() }
  }
  console.log('PASS tree/SVM with declared 35% threshold and mathematically undefined raw ROC AUC')
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
    { casesOverride: [{ ...cases[0], id: 'final-test-row' }, ...cases.slice(1)] },
    { casesOverride: [{ ...cases[0], requested_amount: '200.00' }, ...cases.slice(1)] },
    { casesOverride: [cases[0], cases[0], cases[2]] },
    { casesOverride: cases.slice(0, 2) },
    { casesOverride: [...cases, { ...cases[0], id: 'extra-case' }] },
    { casesOverride: [] },
    { summaryOverride: { ...summary, data_source: 'real' } },
    { summaryOverride: { ...summary, business_approval: true } },
    { summaryOverride: { ...summary, selected_model: 'unknown' } },
    { summaryOverride: { ...summary, threshold: 1.5 } },
    ...['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1', 'f2', 'brier', 'roc_auc'].map((key) => ({
      summaryOverride: { ...summary, comparison: summary.comparison.map((model, index) => index === 0
        ? { ...model, raw: { ...model.raw, [key]: null } } : model) },
    })),
    { summaryOverride: { ...summary, training_scope: 'unknown' } },
    ...(!historical ? [{ summaryOverride: { ...summary, routing: null } }] : []),
  ]) {
    const { context, page, calls } = await fixture('admin', viewport, state)
    try {
      await page.goto(`${origin}${labPath}`)
      await visible(page.getByRole('alert'))
      assert.equal(await page.getByRole('combobox').count(), 0, 'unsafe payload never exposes a case selector')
      assert.equal(calls.filter((call) => call.method === 'POST').length, 0)
    } finally { await context.close() }
  }
  console.log('PASS rejects unknown/duplicate/missing/extra/modified/empty cases and unsafe summaries')

  stage = 'overdue debt gate and policy-response safety guards'
  for (const width of [1440, 390]) {
    const overdue = { ...evaluations['pending-balance-v6'], features: {
      ...evaluations['pending-balance-v6'].features, pending_current: 0, pending_overdue: 1, overdue_rate: 0.125,
    } }
    const { context, page } = await fixture('admin', { width, height: 1000 }, { evaluationOverride: overdue })
    try {
      await page.goto(`${origin}${labPath}`)
      await ready(page)
      await page.getByRole('combobox').selectOption(overdue.case_id)
      await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
      await visible(page.getByText('Solicitud bloqueada por saldo pendiente', { exact: true }))
      await visible(page.getByText(/Modelo no ejecutado\. No se calculan probabilidad, puntaje ni predicción\./))
      assert.equal(await page.getByText('Probabilidad estimada de atraso', { exact: true }).count(), 0)
      assert.equal(await page.getByText('Señal individual del modelo', { exact: true }).count(), 0)
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false)
    } finally { await context.close() }
  }
  for (const [id, patch] of [
    ['illustrative-v6', { threshold: summary.threshold + 0.01 }],
    ['illustrative-v6', { model_called: false }],
    ['illustrative-v6', { decision: 'below_review_threshold' }],
    ['illustrative-v6', { requires_manual_review: false }],
    ['illustrative-v6', { reason: ' ' }],
    ['illustrative-v6', { estimated_late_probability: 1.1 }],
    ['pending-balance-v6', { model_called: true }],
    ['pending-balance-v6', { estimated_late_probability: 0.7 }],
    ['pending-balance-v6', { threshold: 0.2 }],
    ['pending-balance-v6', { predicted_late_payment: 1 }],
    ['pending-balance-v6', { decision: 'requires_owner_review' }],
    ['pending-balance-v6', { requires_manual_review: true }],
    ['no-history-v6', { model_called: true }],
    ['no-history-v6', { estimated_late_probability: 0.7 }],
    ['no-history-v6', { threshold: 0.2 }],
    ['no-history-v6', { predicted_late_payment: 0 }],
    ['no-history-v6', { requires_manual_review: false }],
    ['no-history-v6', { decision: 'blocked_pending_balance' }],
  ]) {
    const { context, page } = await fixture('admin', viewport, { evaluationOverride: { ...evaluations[id], ...patch } })
    try {
      await page.goto(`${origin}${labPath}`)
      await ready(page)
      await page.getByRole('combobox').selectOption(id)
      await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
      await visible(page.getByRole('alert'))
      assert.equal(await page.locator('details').count(), 0, 'invalid policy response never renders results')
      assert.equal(await page.getByText('Probabilidad estimada de atraso', { exact: true }).count(), 0)
    } finally { await context.close() }
  }
  console.log('PASS overdue/current debt and no-history gates; inconsistent decisions, model_called, review flags and signals rejected')

  stage = 'evaluation retry, double click, case-change abort, unmount abort, stale response'
  const state = { evaluationError: true }
  const { context, page, calls } = await fixture('admin', viewport, state)
  let release
  try {
    await page.goto(`${origin}${labPath}`)
    await ready(page)
    const select = page.getByRole('combobox', { name: 'Caso ficticio', exact: true })
    await select.selectOption('illustrative-v6')
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByRole('alert'))
    await delay(200)
    assert.equal(calls.filter((call) => call.method === 'POST').length, 1, 'no automatic POST retry')
    state.evaluationError = false
    state.holdEvaluation = new Promise((resolve) => { release = resolve })
    await page.getByRole('button', { name: 'Reintentar evaluación', exact: true }).evaluate((button) => { button.click(); button.click() })
    await visible(page.getByRole('button', { name: 'Evaluando...', exact: true }))
    await page.waitForFunction(() => window.__v6Requests.filter((entry) => entry.pathname.includes('/evaluate/')).length === 2)
    await delay(100)
    assert.equal(calls.filter((call) => call.method === 'POST').length, 2, 'double click sends one additional POST')
    await select.selectOption('')
    await page.waitForFunction(() => window.__v6Requests.filter((entry) => entry.pathname.includes('/evaluate/'))[1].aborted)
    release()
    delete state.holdEvaluation
    await delay(100)
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'late response cannot display after case change')
    state.evaluationOverride = { ...evaluation, predicted_late_payment: 0, estimated_late_probability: summary.threshold / 2, decision: 'below_review_threshold' }
    await select.selectOption('illustrative-v6')
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByText('Por debajo del umbral de revisión', { exact: true }))
    await visible(page.getByText('Desenlace desconocido', { exact: true }))
    assert.doesNotMatch(await page.locator('main').innerText(), /No atraso|No hubo atraso|Sin atraso estimado/i)
    await select.selectOption('')
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'selection clears previous result')
    await select.selectOption('illustrative-v6')
    state.evaluationOverride = { ...evaluation, actual_late_payment: 0 }
    await page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true }).click()
    await visible(page.getByRole('alert'))
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'reject unexpected known outcome')
    state.evaluationOverride = { ...evaluation, case_id: 'another-case' }
    await page.getByRole('button', { name: 'Reintentar evaluación', exact: true }).click()
    await visible(page.getByRole('alert'))
    assert.equal(await page.getByText('Desenlace desconocido', { exact: true }).count(), 0, 'reject mismatched case response')
    delete state.evaluationOverride
    state.holdEvaluation = new Promise((resolve) => { release = resolve })
    const before = calls.filter((call) => call.method === 'POST').length
    await page.getByRole('button', { name: 'Reintentar evaluación', exact: true }).click()
    await page.waitForFunction((count) => window.__v6Requests.filter((entry) => entry.pathname.includes('/evaluate/')).length === count, before + 1)
    await navigateAway(page)
    assert.equal(await page.evaluate(() => window.__v6Requests.filter((entry) => entry.pathname.includes('/evaluate/')).at(-1).aborted), true, 'unmount aborts POST')
    release()
    delete state.holdEvaluation
    await page.getByRole('link', { name: 'Laboratorio ML V6 - investigación', exact: true }).click()
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
    await loadingFixture.page.waitForFunction(() => window.__v6Requests.length === 2)
    await navigateAway(loadingFixture.page)
    assert.equal(await loadingFixture.page.evaluate(() => window.__v6Requests.every((entry) => entry.aborted)), true)
    releaseLoad()
    await delay(100)
    assert.equal(await loadingFixture.page.getByRole('heading', { name: /seleccionado en desarrollo/ }).count(), 0)
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
      assert.equal(calls.filter((call) => call.pathname.startsWith(apiPrefix)).length, 0, 'no V6 access before authentication')
    } finally { await context.close() }
    console.log('PASS unauthenticated V6 redirects to login without V6 API calls')
  }
  stage = 'final isolation checks'
  assert.deepEqual(unexpected, [], 'no unexpected API routes or mutations')
  assert.deepEqual(runtimeErrors, [], 'no browser runtime exceptions')
  console.log(`PASS ${completed}/6 role/viewport scenarios; flag ${enabled ? 'on' : 'off'}; all API traffic mocked; ${blocked} external requests blocked; no deployment`)
  if (screenshotDirectory && enabled) console.log(`Screenshots: ${screenshotDirectory}`)
} catch (error) {
  // Never print request headers, credentials, browser storage or traces.
  const safeMessage = error instanceof Error ? error.message.split('\n')[0] : 'unknown'
  console.error(`FAIL ${stage}: ${error instanceof assert.AssertionError ? error.message : error.code === 'ERR_MODULE_NOT_FOUND' ? 'Playwright module missing: set PLAYWRIGHT_MODULE_PATH' : `${error?.constructor?.name ?? 'Error'}: ${safeMessage}`}`)
  process.exitCode = 1
} finally {
  if (browser) await browser.close()
}
