import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { setTimeout as delay } from 'node:timers/promises'

const buildDirectory = '/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/credit-history-release'
const origin = 'http://127.0.0.1:4174'
const clientId = '11111111-1111-4111-8111-111111111111'
const creditId = '22222222-2222-4222-8222-222222222222'
const reason = 'Primer fiado conservador con pago acordado.'
const now = new Date().toISOString()
const client = {
  id: clientId, first_name: 'Cliente', last_name: 'Prueba',
  business_name: 'Negocio de prueba', document: '12345678',
  phone: '900000000', address: 'Direccion de prueba', created_at: now,
}
// Deliberately favorable numeric values must not override the manual-review flag.
const evaluation = {
  score: 95, risk: 'bajo', default_probability: 5, confidence: 99,
  recommended_limit: 0, approved: false, requires_manual_review: true,
  recommendation: 'Sin pagos registrados. El primer fiado requiere revision del propietario.',
  factors: [{
    key: 'payment_history_review', label: 'Historial de pagos insuficiente',
    weight: 100, contribution: 0, category: 'riesgo',
    description: 'No existen pagos reales para establecer confianza.',
  }],
  model_version: 'rules-v1', ai_status: 'disabled',
  calculated_at: now, response_time_ms: 12,
}

let stage = 'starting isolated preview'
let browser
let preview
let previewExited = false
let previewFailed = false
let completed = 0
const unexpectedApi = []
const pageErrors = []
const blockedRequests = []

async function visible(locator) {
  await locator.waitFor({ state: 'visible' })
}

async function disabled(button, expected, label) {
  assert.equal(await button.isDisabled(), expected, label)
}

async function verify(role, viewport) {
  const label = `${role}/${viewport.width < 768 ? 'mobile' : 'desktop'}`
  stage = `${label}: setup`
  const context = await browser.newContext({ viewport, serviceWorkers: 'block' })
  const creates = []
  const evaluations = []
  let history = []
  let createdCredit
  try {
    await context.addInitScript(({ role }) => {
      const encode = (value) => btoa(JSON.stringify(value)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_')
      const token = `${encode({ alg: 'none', typ: 'JWT' })}.${encode({ sub: 'browser-fixture', exp: Math.floor(Date.now() / 1000) + 3600 })}.fixture`
      localStorage.removeItem('credify_auth_session')
      sessionStorage.setItem('credify_auth_session', JSON.stringify({
        accessToken: token, refreshToken: token,
        user: { id: 'browser-fixture', nombre: 'Usuario Prueba', correo: 'ui@example.invalid',
          iniciales: 'UP', rol: role, mustChangePassword: false },
      }))
    }, { role })

    // Intercept before navigation, including API URLs compiled with a remote host.
    // No API request is ever continued, and no external resource reaches the network.
    await context.route('**/*', async (route) => {
      const request = route.request()
      const url = new URL(request.url())
      if (/^\/api\/v1(?:\/|$)/.test(url.pathname)) {
        const path = url.pathname.replace(/^\/api\/v1/, '').replace(/\/$/, '')
        const method = request.method()
        const headers = {
          'access-control-allow-origin': origin,
          'access-control-allow-methods': 'GET, POST, OPTIONS',
          'access-control-allow-headers': 'authorization, content-type',
        }
        let json
        let status = 200
        if (method === 'OPTIONS') {
          await route.fulfill({ status: 204, headers })
          return
        }
        if (method === 'GET' && path === '/clients') json = [client]
        else if (method === 'GET' && path === '/settings') json = {
          business_name: 'Prueba aislada', business_phone: '', business_address: '',
          default_credit_term_days: 15, max_credit_amount: '500', due_alerts_enabled: false,
        }
        else if (method === 'GET' && path === '/credits') json = createdCredit ? [createdCredit] : []
        else if (method === 'GET' && ['/payments', '/products'].includes(path)) json = []
        else if (method === 'GET' && path === '/credits/evaluations') json = history
        else if (method === 'GET' && path === '/credits/evaluations/summary') json = {
          total_clients: 1, evaluated_clients: history.length ? 1 : 0, coverage_percent: history.length ? 100 : 0,
        }
        else if (method === 'POST' && path === '/credits/evaluate') {
          evaluations.push(request.postDataJSON())
          history = [{ ...evaluation, id: '33333333-3333-4333-8333-333333333333',
            client_id: clientId, client_name: 'Cliente Prueba', requested_amount: 50, source: 'rules' }]
          json = evaluation
        }
        else if (method === 'POST' && path === '/credits') {
          const body = request.postDataJSON()
          creates.push(body)
          createdCredit = {
            id: creditId, code: 'UI-001', client_id: clientId, client_name: 'Cliente Prueba',
            client_business: client.business_name, client_phone: client.phone,
            original_amount: body.amount, pending_amount: body.amount, paid_amount: 0, paid_percent: 0,
            credit_date: body.credit_date, due_date: body.due_date, status: 'al-dia',
            risk: 'medio', score: 0, recommended_limit: 0, created_at: now, payments: [],
          }
          json = createdCredit
          status = 201
        }
        else {
          unexpectedApi.push(`${label}: ${method} ${path}`)
          json = { detail: 'Unconfigured isolated fixture' }
          status = 501
        }
        await route.fulfill({ status, headers, contentType: 'application/json', body: JSON.stringify(json) })
      } else if (url.origin === origin && !['fetch', 'xhr'].includes(request.resourceType())) {
        await route.continue()
      } else {
        blockedRequests.push(`${label}: ${request.resourceType()}`)
        await route.abort('blockedbyclient')
      }
    })

    const page = await context.newPage()
    // External icon fonts are intentionally blocked; emulate their fixed glyph box.
    await page.addInitScript(() => {
      document.addEventListener('DOMContentLoaded', () => {
        const style = document.createElement('style')
        style.textContent = '.material-symbols-outlined { width: 24px; overflow: hidden; flex-shrink: 0; }'
        document.head.append(style)
      })
    })
    page.setDefaultTimeout(10_000)
    page.on('pageerror', () => pageErrors.push(label))
    stage = `${label}: new-credit evaluation`
    await page.goto(`${origin}/creditos/nuevo?cliente=${clientId}&monto=50`)
    await visible(page.getByRole('heading', { name: 'Registrar nuevo credito' }))
    await page.waitForFunction((id) => document.querySelector('main select')?.value === id, clientId)
    assert.equal(await page.getByRole('spinbutton').inputValue(), '50', 'query amount prefilled')
    await page.getByRole('button', { name: /Calcular score y recomendaci/ }).click()
    const confirm = page.getByRole('button', { name: 'Autorizar excepci\u00f3n y registrar cr\u00e9dito' })
    await visible(confirm)
    await visible(page.getByText('No disponible', { exact: true }))
    await visible(page.getByText('Historial insuficiente', { exact: true }))
    assert.deepEqual(evaluations, [{ client_id: clientId, amount: 50 }], 'evaluation payload')
    await disabled(confirm, true, 'confirmation starts disabled')

    if (role === 'admin') {
      stage = `${label}: explicit authorization gates`
      const checkbox = page.getByRole('checkbox', { name: /Autorizo expresamente/ })
      const explanation = page.getByRole('textbox', { name: /Motivo de la autorizaci/ })
      await explanation.fill(reason)
      await disabled(confirm, true, 'valid reason alone is insufficient')
      await explanation.fill('')
      await checkbox.check()
      await disabled(confirm, true, 'checkbox alone is insufficient')
      await explanation.fill('123456789')
      await disabled(confirm, true, 'nine-character reason is insufficient')
      await explanation.fill(' 123456789 ')
      await disabled(confirm, true, 'whitespace does not count toward ten characters')
      await explanation.fill('1234567890')
      await disabled(confirm, false, 'exactly ten characters plus checkbox enables confirmation')
      await checkbox.uncheck()
      await disabled(confirm, true, 'removing consent disables confirmation')
      assert.equal(creates.length, 0, 'no credit created before authorization')
      await explanation.fill(`  ${reason}  `)
      await checkbox.check()
      await disabled(confirm, false, 'explicit checkbox and valid reason enable confirmation')
      stage = `${label}: mocked create payload`
      const request = page.waitForRequest((request) =>
        request.method() === 'POST' && new URL(request.url()).pathname.replace(/\/$/, '') === '/api/v1/credits')
      const response = page.waitForResponse((response) => response.request().method() === 'POST'
        && new URL(response.url()).pathname.replace(/\/$/, '') === '/api/v1/credits')
      await confirm.click()
      const body = (await request).postDataJSON()
      assert.equal(body.client_id, clientId, 'create client')
      assert.equal(body.amount, 50, 'create amount')
      assert.equal(body.manual_override, true, 'create manual override')
      assert.equal(body.exception_reason, reason, 'create trimmed exception reason')
      assert.match(body.credit_date, /^\d{4}-\d{2}-\d{2}$/, 'credit date')
      assert.ok(body.due_date > body.credit_date, 'due date follows credit date')
      // Wait for the fixture, not successful navigation or detail-page rendering.
      await response
      assert.equal(creates.length, 1, 'exactly one mocked creation')
    } else {
      stage = `${label}: history exception is admin-only`
      await visible(page.getByText(/Solo un administrador puede autorizar el primer fiado sin historial/))
      assert.equal(await page.getByRole('checkbox', { name: /Autorizo expresamente/ }).count(), 0, 'operator has no consent control')
      assert.equal(await page.getByRole('textbox', { name: /Motivo de la autorizaci/ }).count(), 0, 'operator has no reason control')
      await disabled(confirm, true, 'operator cannot confirm')
      await confirm.evaluate((button) => button.click())
      assert.equal(creates.length, 0, 'operator sends no create request')
    }

    stage = `${label}: evaluation presentation`
    await page.goto(`${origin}/evaluacion-crediticia?cliente=${clientId}`)
    await visible(page.getByRole('heading', { name: 'Evaluaci\u00f3n crediticia', exact: true }))
    await page.waitForFunction((id) => document.querySelector('main select')?.value === id, clientId)
    await page.getByRole('spinbutton').fill('50')
    await page.getByRole('button', { name: /Evaluar cr/ }).click()
    await visible(page.getByText('Historial insuficiente', { exact: true }))
    await visible(page.getByText('No disponible', { exact: true }))
    await visible(page.getByText('No concluyente', { exact: true }))
    await visible(page.getByText('Sin asignar', { exact: true }))
    await visible(page.getByText('Revisi\u00f3n manual', { exact: true }))
    await visible(page.getByRole('cell', { name: 'Sin historial', exact: true }))
    await visible(page.getByRole('cell', { name: 'Revisi\u00f3n del propietario', exact: true }))
    const text = await page.locator('main').innerText()
    assert.doesNotMatch(text, /riesgo\s+(?:muy\s+)?bajo|resultado favorable|cr[e\u00e9]dito recomendado|95\/100|5\/100|\b5\s*%/i, 'no misleading low-risk score or probability')
    assert.equal(evaluations.length, 2, 'both pages evaluated')
    assert.deepEqual(evaluations[1], { client_id: clientId, amount: 50 }, 'simulator payload')
    assert.equal(creates.length, role === 'admin' ? 1 : 0, 'no extra credit creation')
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'evaluation has no horizontal page overflow: ' + JSON.stringify(await page.evaluate(() => Array.from(document.querySelectorAll('main *')).filter(el => el.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(el => [el.tagName, el.className, el.getBoundingClientRect().right]))))
    completed += 1
    console.log(`PASS ${label}: ${role === 'admin' ? 'consent/reason gates + S/50 override payload' : 'admin-only message + confirmation blocked'}; insufficient-history presentation`)
  } finally {
    await context.close()
  }
}

try {
  // Bash exec keeps the preview PID owned by this runner for reliable cleanup.
  preview = spawn('/bin/bash', ['-c', 'exec node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4174 --strictPort'], {
    cwd: buildDirectory, stdio: 'ignore',
  })
  preview.on('exit', () => { previewExited = true })
  preview.on('error', () => { previewFailed = true })
  let ready = false
  for (let attempt = 0; attempt < 100; attempt += 1) {
    await delay(100)
    assert.ok(!previewExited && !previewFailed, 'isolated preview failed to start (port must be free)')
    try { ready = (await fetch(origin)).ok } catch { /* Preview is still starting. */ }
    if (ready) break
  }
  assert.ok(ready, 'isolated preview readiness timeout')
  console.log('PASS isolated production preview ready at 127.0.0.1:4174')
  stage = 'loading required Playwright module (index.mjs must exist at the specified absolute path)'
  const { chromium } = await import('/var/folders/sx/_6ljw37n2_j9hk2f_vtqplj40000gn/T/opencode/apf2-browser/node_modules/playwright/index.mjs')
  stage = 'launching Chromium'
  browser = await chromium.launch({ headless: true })
  for (const role of ['admin', 'operator']) {
    for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
      await verify(role, viewport)
    }
  }
  stage = 'final isolation and runtime checks'
  assert.equal(unexpectedApi.length, 0, `unexpected fixture routes: ${unexpectedApi.join(', ')}`)
  assert.equal(pageErrors.length, 0, 'no browser runtime exceptions')
  console.log(`PASS ${completed}/4 scenarios; all API traffic mocked; external requests blocked (${blockedRequests.length}); no browser runtime exceptions`)
} catch (error) {
  // Never emit request headers, storage, browser traces, or credential values.
  console.error(`FAIL ${stage}: ${error instanceof assert.AssertionError ? error.message : error.code === 'ERR_MODULE_NOT_FOUND' ? 'required browser dependency missing' : 'browser verification failed'}`)
  process.exitCode = 1
} finally {
  try {
    if (browser) await browser.close()
  } finally {
    if (preview && !previewExited && !previewFailed) {
      const stopped = new Promise((resolve) => preview.once('exit', resolve))
      preview.kill('SIGTERM')
      await Promise.race([stopped, delay(3000)])
      if (!previewExited) {
        preview.kill('SIGKILL')
        await stopped
      }
    }
    console.log(`Preview ${previewExited ? 'stopped' : 'not running'}; no deployment performed`)
  }
}
