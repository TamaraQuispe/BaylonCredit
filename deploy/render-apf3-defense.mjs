// Offline export from the same content/design as the editable PPTX, not a native PPT renderer.
import assert from 'node:assert/strict'
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import path from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const root = process.argv[2]
assert.ok(root)
const output = path.join(root, 'sustentacion')
const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 })
  await page.route('**/*', route => route.abort())
  const name = 'APF3_TD_Grupo2_ML_Innovacion'
  await page.setContent(await readFile(path.join(output, name + '.html'), 'utf8'))
  await page.emulateMedia({ media: 'print' })
  await page.evaluate(() => document.fonts.ready)
  assert.equal(await page.locator('.slide').count(), 13)
  const overflows = await page.locator('.txt, .tbl .tr>div').evaluateAll(elements => elements
    .filter(element => element.scrollHeight > element.clientHeight + 2 || element.scrollWidth > element.clientWidth + 2)
    .map(element => ({ slide: element.closest('.slide').dataset.number, text: element.textContent, height: element.clientHeight, neededHeight: element.scrollHeight })))
  await writeFile(path.join(output, 'revision-diseno.json'), JSON.stringify({ overflows }, null, 2))
  assert.deepEqual(overflows, [], 'Slide text overflow; fix before publishing')
  await page.pdf({ path: path.join(output, name + '.pdf'), preferCSSPageSize: true, printBackground: true })
  await mkdir(path.join(output, 'vistas'), { recursive: true })
  for (let index = 0; index < 13; index++) {
    await page.locator('.slide').nth(index).screenshot({ path: path.join(output, 'vistas', `${String(index + 1).padStart(2, '0')}.png`) })
  }
  for (const document of ['APF3_Grupo2_Guion_12min', 'APF3_Grupo2_Ficha_Calibracion_Meta', 'APF3_Ficha_Propietario_Baylon']) {
    await page.setContent(await readFile(path.join(output, document + '.html'), 'utf8'))
    await page.evaluate(() => document.fonts.ready)
    await page.pdf({
      path: path.join(output, document + '.pdf'), preferCSSPageSize: true, printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: '<div style="font:8px Arial;color:#64748b;width:100%;text-align:center">APF3 · Grupo 2 · Material de preparación · Revisión humana pendiente</div>',
      footerTemplate: '<div style="font:9px Arial;color:#64748b;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    })
  }
  console.log(JSON.stringify({ slides: 13, text_overflows: 0, documents: 3 }))
} finally {
  await browser.close()
}
