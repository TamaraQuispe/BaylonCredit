// Render only the self-contained local report; no public service requests.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE_PATH || 'playwright')
const output = process.argv[2]
assert.ok(output, 'Report directory required')
const name = 'APF3_TD_Grupo2_ML_Innovacion_Borrador'
const browser = await chromium.launch()
try {
  const page = await browser.newPage({ viewport: { width: 800, height: 1120 } })
  await page.route('**/*', route => route.abort())
  await page.setContent(await readFile(path.join(output, name + '.html'), 'utf8'))
  await page.emulateMedia({ media: 'print' })
  await page.evaluate(() => document.fonts.ready)
  const pages = await page.locator('.page').evaluateAll(elements => elements.map(element => ({
    title: element.querySelector('h1,h2')?.textContent,
    height_px: Math.ceil(element.getBoundingClientRect().height),
    width_px: Math.ceil(element.getBoundingClientRect().width),
  })))
  await page.pdf({
    path: path.join(output, name + '.pdf'), preferCSSPageSize: true, printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div style="font:8px Arial;color:#64748b;width:100%;text-align:center">APF3 · Grupo 2 · BORRADOR · Datos simulados</div>',
    footerTemplate: '<div style="font:9px Arial;color:#64748b;width:100%;text-align:center"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
  })
  await page.locator('.page').nth(5).screenshot({ path: path.join(output, 'vista-eda.png') })
  await writeFile(path.join(output, 'verificacion-render.json'), JSON.stringify({ pages }, null, 2))
  const manifestPath = path.join(output, 'manifest.json')
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
  for (const file of [name + '.pdf', 'vista-eda.png', 'verificacion-render.json']) {
    manifest.files[file] = createHash('sha256').update(await readFile(path.join(output, file))).digest('hex')
  }
  await writeFile(manifestPath, JSON.stringify(manifest, null, 2))
  console.log(JSON.stringify({ pdf: path.join(output, name + '.pdf'), sections: pages.length }))
} finally {
  await browser.close()
}
