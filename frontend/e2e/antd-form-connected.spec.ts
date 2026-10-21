/**
 * Regression test: antd's "Instance created by `useForm` is not connected to any
 * Form element" warning must not appear when a page loads.
 *
 * Why this exists
 * ---------------
 * Three static-data pages read a form instance while its <Form> was unmounted:
 *
 *   const queryParams = useCallback(() => {
 *     const adv = advancedForm.getFieldsValue()   // <- here
 *     ...
 *   }, [..., advancedForm])
 *   ...
 *   {showAdvanced && (<Form form={advancedForm}>)}  // starts false
 *
 * react-query runs queryParams() on mount, so the instance was used before its
 * Form ever existed. antd's useForm arms a 0ms timeout at that moment and warns
 * if `formHooked` is still false when it fires — and because the Form never
 * mounted, it was.
 *
 * Both halves are needed for the warning: an instance that is *used* while its
 * Form is *absent*. That is why earlier probes that revealed the Form right after
 * calling a method came back green — React flushed the state update before the
 * macrotask ran, so the Form mounted in time.
 *
 * A correct seam for this bug is therefore a real page render, not a unit test:
 * the behaviour depends on mount ordering, which only exists in a browser.
 */
import { test, expect } from '@playwright/test'

const NEEDLE = 'not connected to any Form element'

// Pages that read a conditional <Form>'s instance from a mount-time callback.
// Extend this list when another page adopts the same shape.
const PAGES = [
  '/quality/static-data/chrom-column',
  '/quality/static-data/hplc-reference',
  '/quality/static-data/medium',
]

for (const path of PAGES) {
  test(`no useForm "not connected" warning on ${path}`, async ({ page }) => {
    const warns: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error' && m.text().includes(NEEDLE)) warns.push(m.text())
    })

    await page.goto(path, { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(4000)

    // Guard against a false green: an unauthenticated run lands on /login, where
    // none of this markup renders and nothing could warn.
    expect(new URL(page.url()).pathname, `${path} redirected away`).toBe(path)
    expect(warns, `${path} logged the antd "not connected" warning:\n${warns.join('\n')}`).toHaveLength(0)
  })
}
