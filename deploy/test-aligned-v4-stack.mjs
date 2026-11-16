// Local, disposable real-stack E2E. No compose, mocks, persistent volumes or remote deployment.
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { randomBytes, createHash } from 'node:crypto'
import { mkdir, readFile, readdir, stat, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createServer } from 'node:net'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { setTimeout as delay } from 'node:timers/promises'

const root = fileURLToPath(new URL('../', import.meta.url))
const temp = '/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode'
const prefix = `credify-v4-check-${Date.now()}-${randomBytes(4).toString('hex')}`
const output = path.join(temp, 'v4-stack-check', prefix)
const label = `credify.v4-check.owner=${prefix}`
const images = { api: 'credify-demo-academic-api:v4', frontend: 'credify-demo-academic-frontend:v4', database: 'postgres:17-alpine' }
const bundle = path.join(root, 'academic/v4')
const evidence = { status: 'failed', project: prefix, scope: 'real Docker/Postgres/JWT/browser/model; no mocks', images: {}, requests: [], screenshots: [], final_inference: false }
const owned = []
let networkCreated = false
let browser
let relay
const relayConnections = new Set()
let stage = 'preflight'
let origin
let interrupted = false
const secrets = {
  POSTGRES_PASSWORD: randomBytes(32).toString('hex'),
  JWT_SECRET_KEY: randomBytes(48).toString('hex'),
  DEMO_USER_PASSWORD: randomBytes(24).toString('hex'),
}
const env = { ...process.env, ...secrets, POSTGRES_USER: 'demo', POSTGRES_DB: 'credify_demo',
  ENVIRONMENT: 'staging', DEMO_MODE: 'true', CREDIT_ML_ENABLED: 'false', OPENROUTER_ENABLED: 'false',
  WHATSAPP_ENABLED: 'false', ACADEMIC_ML_LAB_ENABLED: 'false', ACADEMIC_ML_V4_ENABLED: 'true',
  ACADEMIC_ML_V4_DIR: '/app/academic-v4', OMP_NUM_THREADS: '1', OPENBLAS_NUM_THREADS: '1',
  DATABASE_URL: `postgresql+asyncpg://demo:${secrets.POSTGRES_PASSWORD}@database:5432/credify_demo` }

// Subprocess output is retained privately, never forwarded: failures can contain DB credentials.
function docker(args, timeout = 60_000) {
  return new Promise((resolve, reject) => {
    const child = spawn('docker', args, { env, stdio: ['ignore', 'pipe', 'pipe'] })
    let stdout = ''
    child.stdout.on('data', (data) => { stdout += data })
    child.stderr.resume()
    const timer = setTimeout(() => child.kill('SIGKILL'), timeout)
    child.on('error', () => { clearTimeout(timer); reject(new Error('Docker invocation failed')) })
    child.on('close', (code) => {
      clearTimeout(timer)
      if (code === 0) resolve(stdout.trim())
      else reject(new Error('Docker command failed'))
    })
  })
}
const inspect = async (name) => JSON.parse(await docker(['inspect', name]))[0]
const apiEnv = Object.keys(env).filter((key) => !Object.hasOwn(process.env, key) || env[key] !== process.env[key])
  .flatMap((key) => ['--env', key])

async function hashes() {
  const result = {}
  for (const name of (await readdir(bundle)).sort()) {
    assert.ok((await stat(path.join(bundle, name))).isFile(), 'bundle contains only files')
    result[name] = createHash('sha256').update(await readFile(path.join(bundle, name))).digest('hex')
  }
  return result
}

async function create(suffix, options, image, command = []) {
  assert.ok(!interrupted, 'interrupted')
  const name = `${prefix}-${suffix}`
  // Register before create so cleanup also covers interrupted starts.
  owned.push(name)
  await docker(['create', '--name', name, '--label', label, '--network', prefix,
    '--log-driver', 'none', ...options, image, ...command])
  await docker(['start', name])
  return name
}

async function waitFor(operation, timeout = 90_000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline && !interrupted) {
    try { if (await operation()) return } catch { /* Readiness polling only. */ }
    await delay(750)
  }
  throw new Error('Readiness timeout')
}

async function job(suffix, command) {
  const name = await create(suffix, ['--memory', '256m', '--read-only', '--tmpfs', '/tmp:rw,nosuid,noexec,size=32m',
    ...apiEnv, '--mount', `type=bind,source=${bundle},target=/app/academic-v4,readonly`], images.api, command)
  assert.equal(await docker(['wait', name], 120_000), '0', `${suffix} exit status`)
  assert.equal((await inspect(name)).State.OOMKilled, false, `${suffix} no OOM`)
}

function record(method, pathname, status) { evidence.requests.push({ method, pathname, status }) }
async function getJSON(page, pathname, token) {
  const result = await page.evaluate(async ({ pathname, token }) => {
    const response = await fetch(pathname, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    return { status: response.status, json: await response.json() }
  }, { pathname, token })
  record('GET', pathname, result.status)
  assert.equal(result.status, 200, 'authenticated read status')
  return result.json
}

async function counts(page, token) {
  const result = {}
  for (const endpoint of ['credits', 'credits/evaluations', 'clients', 'payments']) {
    const rows = await getJSON(page, `/api/v1/${endpoint}`, token)
    assert.ok(Array.isArray(rows) && rows.length < 50, 'unpaginated tiny seeded dataset')
    result[endpoint] = rows.length
  }
  return result
}

async function testViewport(viewport) {
  const mode = viewport.width < 768 ? 'mobile' : 'desktop'
  stage = `${mode}: browser authentication`
  const context = await browser.newContext({ viewport, serviceWorkers: 'block' })
  const mutations = []
  const external = []
  const runtimeErrors = []
  // Only prevent outbound traffic; never fulfill or mock any API or resource.
  await context.route('**/*', async (route) => {
    const request = route.request()
    const url = new URL(request.url())
    if (url.origin !== origin) {
      external.push(url.hostname)
      return route.abort('blockedbyclient')
    }
    if (url.pathname.startsWith('/api/') && !['GET', 'HEAD', 'OPTIONS'].includes(request.method())) {
      mutations.push({ method: request.method(), pathname: url.pathname, bodyless: request.postData() === null })
    }
    return route.continue()
  })
  const page = await context.newPage()
  page.setDefaultTimeout(20_000)
  page.on('pageerror', (error) => runtimeErrors.push(error.name))
  page.on('response', (response) => {
    const url = new URL(response.url())
    if (url.origin === origin && url.pathname.startsWith('/api/')) record(response.request().method(), url.pathname, response.status())
  })
  try {
    await page.goto(`${origin}/laboratorio-academico/v4`)
    await page.waitForURL(`${origin}/iniciar-sesion`)
    const anonymous = await page.evaluate(async () => {
      const results = []
      for (const [method, pathname] of [['GET', '/summary'], ['GET', '/cases'], ['POST', '/evaluate/illustrative-v4']]) {
        const response = await fetch(`/api/v1/academic-ml/v4${pathname}`, { method })
        results.push({ method, pathname, status: response.status })
      }
      return results
    })
    assert.ok(anonymous.every((item) => item.status === 401), 'anonymous matrix 401')
    evidence.auth_matrix ??= { anonymous, authenticated_role: 'operator', ui_login: true }
    mutations.length = 0
    await page.locator('#email').fill('docente@example.com')
    await page.locator('#password').fill(secrets.DEMO_USER_PASSWORD)
    const loginPromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/auth/login')
    await page.locator('button[type="submit"]').click()
    const loginResponse = await loginPromise
    assert.equal(loginResponse.status(), 200, 'UI real login status')
    const login = await loginResponse.json()
    assert.equal(login.user.role, 'operator', 'seed role')
    assert.ok(typeof login.access_token === 'string', 'real token received')
    await page.waitForURL(`${origin}/inicio`)
    const before = await counts(page, login.access_token)
    assert.deepEqual(before, { credits: 0, 'credits/evaluations': 0, clients: 3, payments: 0 }, 'fresh seeded baseline')
    stage = `${mode}: real V4 summary and tables`
    const summaryPromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/academic-ml/v4/summary')
    const casesPromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/academic-ml/v4/cases')
    await page.goto(`${origin}/laboratorio-academico/v4`)
    const summaryResponse = await summaryPromise
    assert.equal(summaryResponse.status(), 200, 'summary status')
    const summary = await summaryResponse.json()
    const casesResponse = await casesPromise
    assert.equal(casesResponse.status(), 200, 'cases status')
    const cases = await casesResponse.json()
    assert.equal(summary.version, 'academic-owner-aligned-v4', 'version')
    assert.equal(summary.final_labeled_rows, 259, 'known FINAL rows')
    assert.equal(summary.development_rows, 552, 'resolved development rows')
    assert.ok(Number.isInteger(summary.final_unknown) && summary.final_unknown > 0, 'unknown FINAL rows separate from known labels')
    assert.equal(summary.research_only, true, 'research only')
    assert.equal(summary.business_approval, false, 'no commercial approval')
    assert.equal(summary.data_source, 'synthetic', 'synthetic source')
    assert.deepEqual(summary.comparison.map((row) => row.family), ['svm', 'tree', 'most_frequent', 'constant_1'], 'four models')
    assert.deepEqual(summary.comparison[0].raw.confusion_matrix, [[80, 114], [4, 61]], 'frozen raw matrix')
    assert.equal(summary.comparison[3].policy.metrics.f2, 0.622568093385214, 'frozen policy F2')
    assert.deepEqual(cases.map((item) => [item.id, item.requested_amount]), [['illustrative-v4', '20.00']], 'only illustrative case')
    await page.getByRole('heading', { name: 'SVM seleccionado en desarrollo', exact: true }).waitFor()
    for (const [name, policy] of [['Raw: sin pol\u00edtica de revisi\u00f3n', false], ['Pol\u00edtica top-5: m\u00e9tricas precalculadas', true]]) {
      const table = page.getByRole('table', { name, exact: true })
      assert.equal(await table.getByRole('columnheader').count(), 5, 'four UI model columns')
      for (const [key, label] of [['f2', 'F2'], ['recall', 'Sensibilidad (recall)'], ['roc_auc', 'ROC AUC']]) {
        const expected = summary.comparison.map((row) => (policy ? row.policy.metrics : row.raw)[key])
          .map((value) => value == null ? 'No disponible' : value.toLocaleString('es-PE', { maximumFractionDigits: 4 }))
        assert.deepEqual(await table.getByRole('row').filter({ has: page.getByRole('rowheader', { name: label, exact: true }) }).getByRole('cell').allTextContents(), expected, 'UI metrics match API')
      }
    }
    const select = page.getByRole('combobox', { name: 'Caso ficticio', exact: true })
    const evaluate = page.getByRole('button', { name: 'Evaluar caso ficticio', exact: true })
    assert.equal(await evaluate.isDisabled(), true, 'explicit selection required')
    assert.equal(await page.locator('main input, main textarea').count(), 0, 'no arbitrary inputs')
    await select.selectOption('illustrative-v4')
    stage = `${mode}: illustrative inference`
    const evaluatedPromise = page.waitForResponse((response) => new URL(response.url()).pathname === '/api/v1/academic-ml/v4/evaluate/illustrative-v4')
    await evaluate.click()
    const evaluatedResponse = await evaluatedPromise
    assert.equal(evaluatedResponse.status(), 200, 'illustrative status')
    const evaluated = await evaluatedResponse.json()
    assert.equal(evaluated.estimated_late_probability, 0.11922453881690649, 'frozen score')
    assert.equal(evaluated.threshold, 0.1, 'threshold')
    assert.equal(evaluated.actual_late_payment, null, 'unknown outcome')
    assert.equal(evaluated.predicted_late_payment, 1, 'review candidate')
    assert.equal(evaluated.review_policy_applied, false, 'individual score is not top-5')
    assert.equal(evaluated.business_approval, false, 'inference not commercial')
    await page.getByText('Desenlace desconocido', { exact: true }).waitFor()
    await page.getByText(evaluated.estimated_late_probability.toLocaleString('es-PE', { style: 'percent', maximumFractionDigits: 1 }), { exact: true }).waitFor()
    await page.getByText('Candidato a revisi\u00f3n por umbral', { exact: true }).waitFor()
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'no page horizontal overflow')
    const after = await counts(page, login.access_token)
    assert.deepEqual(after, before, 'no business record mutations')
    assert.deepEqual(mutations, [
      { method: 'POST', pathname: '/api/v1/auth/login', bodyless: false },
      { method: 'POST', pathname: '/api/v1/academic-ml/v4/evaluate/illustrative-v4', bodyless: true },
    ], 'only login and one bodyless illustrative POST; no commercial evaluate/create')
    assert.deepEqual(runtimeErrors, [], 'no browser runtime errors')
    await page.evaluate(() => window.scrollTo(0, 0))
    const screenshot = path.join(output, `${mode}.png`)
    await page.screenshot({ path: screenshot, fullPage: true })
    evidence.screenshots.push(screenshot)
    evidence[mode] = { status: 'passed', viewport, before, after, score: evaluated.estimated_late_probability,
      threshold: evaluated.threshold, actual_late_payment: null, mutations, external_blocked: external.length }
    evidence.summary = summary
  } finally { await context.close() }
}

for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => {
  interrupted = true
  browser?.close().catch(() => {})
})

try {
  assert.ok((await stat(temp)).isDirectory(), 'temporary parent exists')
  await mkdir(output, { recursive: true })
  const seed = await readFile(path.join(root, 'backend/app/scripts/seed_demo.py'), 'utf8')
  assert.ok(seed.includes('docente@example.com') && seed.includes('role=UserRole.OPERATOR'), 'verified seed identity')
  for (const [kind, image] of Object.entries(images)) {
    const data = JSON.parse(await docker(['image', 'inspect', image]))[0]
    assert.equal(data.Architecture, 'arm64', 'native image architecture')
    evidence.images[kind] = { tag: image, id: data.Id, architecture: data.Architecture }
    images[kind] = data.Id
  }
  evidence.bundle_before = await hashes()
  const modulePath = process.env.PLAYWRIGHT_MODULE_PATH
  assert.ok(modulePath && path.isAbsolute(modulePath), 'absolute PLAYWRIGHT_MODULE_PATH required')
  const { chromium } = await import(pathToFileURL(modulePath).href)
  evidence.existing_before = JSON.parse(await docker(['ps', '--format', '{{json .}}']).then((text) => `[${text.split('\n').filter(Boolean).join(',')}]`))
    .map((item) => ({ id: item.ID, name: item.Names, ports: item.Ports }))
  await docker(['network', 'create', '--internal', '--label', label, prefix])
  networkCreated = true
  const network = JSON.parse(await docker(['network', 'inspect', prefix]))[0]
  assert.equal(network.Internal, true, 'internal network')
  evidence.network_internal = network.Internal
  stage = 'ephemeral PostgreSQL readiness'
  await create('database', ['--network-alias', 'database', '--memory', '128m',
    '--tmpfs', '/var/lib/postgresql/data:rw,nosuid,size=128m', '--env', 'POSTGRES_PASSWORD', '--env', 'POSTGRES_USER', '--env', 'POSTGRES_DB'], images.database)
  await waitFor(async () => { await docker(['exec', `${prefix}-database`, 'pg_isready', '-U', 'demo', '-d', 'credify_demo']); return true })
  stage = 'real Alembic migration'
  await job('migrate', ['alembic', 'upgrade', 'head'])
  stage = 'real demo seed'
  await job('seed', ['python', '-m', 'app.scripts.seed_demo'])
  stage = 'API and Nginx readiness'
  await create('api', ['--network-alias', 'api', '--memory', '256m', '--read-only', '--tmpfs', '/tmp:rw,nosuid,noexec,size=32m',
    ...apiEnv, '--mount', `type=bind,source=${bundle},target=/app/academic-v4,readonly`], images.api,
  ['uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000', '--workers', '1', '--no-access-log'])
  await waitFor(async () => { await docker(['exec', `${prefix}-api`, 'python', '-c', "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3)"]); return true })
  await create('frontend', ['--memory', '32m', '-p', '127.0.0.1::8080'], images.frontend)
  const frontend = await inspect(`${prefix}-frontend`)
  const binding = frontend.NetworkSettings.Ports['8080/tcp']
  evidence.port_binding = { configured: frontend.HostConfig.PortBindings['8080/tcp'], actual: binding }
  if (binding.length === 0) {
    // Docker 29 suppresses published ports on internal-only endpoints. Preserve that
    // isolation and carry unmodified browser TCP bytes through exec to real Nginx.
    await docker(['exec', `${prefix}-frontend`, 'sh', '-c', 'command -v nc'])
    relay = createServer((socket) => {
      const child = spawn('docker', ['exec', '-i', `${prefix}-frontend`, 'nc', '127.0.0.1', '8080'],
        { stdio: ['pipe', 'pipe', 'ignore'] })
      relayConnections.add(socket)
      socket.pipe(child.stdin)
      child.stdout.pipe(socket)
      child.stdin.on('error', () => socket.destroy())
      child.on('error', () => socket.destroy())
      child.on('close', () => socket.end())
      socket.on('error', () => child.kill())
      socket.on('close', () => { child.kill(); relayConnections.delete(socket) })
    })
    await new Promise((resolve, reject) => {
      relay.once('error', reject)
      relay.listen(0, '127.0.0.1', resolve)
    })
    assert.equal(relay.address().address, '127.0.0.1', 'TCP relay loopback only')
    origin = `http://127.0.0.1:${relay.address().port}`
    evidence.transport = 'Loopback ephemeral TCP relay via docker exec nc to real Nginx; internal network unchanged; no HTTP interception'
  } else {
    assert.equal(binding.length, 1, 'one dynamic published port')
    assert.equal(binding[0].HostIp, '127.0.0.1', 'loopback only')
    origin = `http://127.0.0.1:${binding[0].HostPort}`
    evidence.transport = 'Docker dynamic loopback published port'
  }
  evidence.origin = origin
  await waitFor(async () => (await fetch(`${origin}/health/ready`, { signal: AbortSignal.timeout(4000) })).ok)
  browser = await chromium.launch({ headless: true })
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) await testViewport(viewport)
  stage = 'post-model memory and isolation verification'
  evidence.memory_after_model = (await docker(['stats', '--no-stream', '--format', '{{json .}}', ...['api', 'frontend', 'database'].map((kind) => `${prefix}-${kind}`)]))
    .split('\n').filter(Boolean).map((line) => {
      const item = JSON.parse(line)
      return { name: item.Name, memory_usage: item.MemUsage, memory_percent: item.MemPerc, pids: item.PIDs }
    })
  evidence.memory_note = 'Single local sample after two illustrative inferences; not a capacity or concurrency promise.'
  evidence.containers = []
  for (const kind of ['api', 'frontend', 'database']) {
    const item = await inspect(`${prefix}-${kind}`)
    assert.equal(item.State.OOMKilled, false, 'no OOM')
    assert.equal(item.State.Running, true, 'running')
    assert.deepEqual(Object.keys(item.NetworkSettings.Networks), [prefix], 'dedicated internal network only')
    assert.ok(item.Mounts.every((mount) => mount.Type !== 'volume'), 'no Docker volumes')
    if (kind === 'api') {
      assert.equal(item.HostConfig.Memory, 256 * 1024 * 1024, 'API limit')
      assert.equal(item.HostConfig.ReadonlyRootfs, true, 'read-only runtime and bundle')
      assert.ok(item.Mounts.some((mount) => mount.Destination === '/app/academic-v4' && mount.RW === false), 'read-only bundle mount')
    }
    if (kind === 'frontend') assert.equal(item.HostConfig.Memory, 32 * 1024 * 1024, 'frontend limit')
    evidence.containers.push({ name: item.Name, image_id: item.Image, memory_limit_bytes: item.HostConfig.Memory, oom_killed: item.State.OOMKilled })
  }
  evidence.bundle_after = await hashes()
  assert.deepEqual(evidence.bundle_after, evidence.bundle_before, 'bundle unchanged')
  evidence.status = 'passed'
} catch (error) {
  evidence.failed_stage = stage
  evidence.error_type = error.name
  // Assertion labels are authored here; third-party messages and assertion values stay private.
  evidence.failed_check = error instanceof assert.AssertionError ? error.message.split('\n')[0] : 'Operation failed; subprocess details withheld'
  process.exitCode = 1
} finally {
  await browser?.close().catch(() => {})
  for (const socket of relayConnections) socket.destroy()
  if (relay) await new Promise((resolve) => relay.close(resolve))
  const failures = []
  for (const name of owned.reverse()) {
    try {
      const item = await inspect(name).catch(() => null)
      if (!item) continue
      assert.equal(item.Config.Labels?.['credify.v4-check.owner'], prefix, 'cleanup ownership')
      await docker(['rm', '-f', name])
    } catch { failures.push(name) }
  }
  if (networkCreated) {
    try {
      const item = JSON.parse(await docker(['network', 'inspect', prefix]))[0]
      assert.equal(item.Labels?.['credify.v4-check.owner'], prefix, 'network cleanup ownership')
      await docker(['network', 'rm', prefix])
    } catch { failures.push(prefix) }
  }
  evidence.cleanup = { status: failures.length ? 'failed' : 'passed', failed_resources: failures }
  try {
    const leftovers = await docker(['ps', '-aq', '--filter', `label=${label}`])
    assert.equal(leftovers, '', 'no owned containers remain')
    assert.equal(await docker(['network', 'ls', '-q', '--filter', `label=${label}`]), '', 'no owned networks remain')
    const running = await docker(['ps', '-q', '--no-trunc'])
    assert.ok((evidence.existing_before || []).every((item) => running.split('\n').some((id) => id.startsWith(item.id))), 'existing containers still running')
    evidence.existing_services_untouched = true
  } catch { evidence.cleanup.status = 'failed'; process.exitCode = 1 }
  if (failures.length) { evidence.status = 'failed'; process.exitCode = 1 }
  if (interrupted) { evidence.status = 'interrupted'; process.exitCode = 1 }
  const serialized = JSON.stringify(evidence, null, 2) + '\n'
  await writeFile(path.join(output, 'evidence.json'), serialized)
  console.log(serialized)
}
