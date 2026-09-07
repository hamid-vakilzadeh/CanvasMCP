import { test, expect } from '@playwright/test';

async function selectStudent(page, id='7') {
  await page.locator('#course').selectOption('42');
  await page.locator('#student').selectOption(id);
  await expect(page.locator('.identity h2')).toHaveText(`Synthetic Student ${id}`);
}

test('localhost selection, optional evidence, filters, keyboard and responsive layout', async({page})=>{
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/#synthetic-ui-session');
  await selectStudent(page);
  await expect(page.locator('.main-metric strong')).toHaveText('81.25%');
  await page.locator('#assignment-filter').selectOption('missing');
  await expect(page.locator('#assignment-rows tr')).toHaveCount(1);
  await page.locator('#assignment-filter').selectOption('all');
  await page.getByText('Rubrics & instructor feedback',{exact:true}).click();
  await expect(page.locator('#detail-rubrics')).toContainText('Reasoning about control limitations');
  await page.getByText('Learning outcomes',{exact:true}).click();
  await expect(page.locator('#detail-outcomes')).toContainText('Evaluate control limitations');
  await page.locator('#refresh').focus(); await page.keyboard.press('Tab');
  await expect(page.locator('#assignment-search')).toBeFocused();
  await page.screenshot({path:'/private/tmp/canvas-dashboard-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.screenshot({path:'/private/tmp/canvas-dashboard-mobile.png',fullPage:true});
  expect(errors).toEqual([]);
});

test('a slower student response cannot overwrite the new selection',async({page})=>{
  await page.route('**/api',async route=>{
    const data=route.request().postDataJSON();
    if(data.action==='report'&&data.student_id==='7') {
      const response=await route.fetch(); await new Promise(r=>setTimeout(r,700));
      await route.fulfill({response});
    } else await route.continue();
  });
  await page.goto('/#synthetic-ui-session');
  await page.locator('#course').selectOption('42');
  await page.locator('#student').selectOption('7');
  await page.locator('#student').selectOption('8');
  await expect(page.locator('.identity h2')).toHaveText('Synthetic Student 8');
  await page.waitForTimeout(900);
  await expect(page.locator('.identity h2')).toHaveText('Synthetic Student 8');
  await expect(page.locator('.main-metric strong')).toHaveText('67.5%');
});

test('embedded SDK adapter handles tool namespace and unsupported message capability',async({page})=>{
  const errors=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/test-host');
  const frame=page.frameLocator('#app');
  await selectStudent(frame);
  await expect(frame.locator('#connection')).toContainText('MCP host');
  await frame.locator('#start-review').click();
  await expect(frame.locator('.job')).toHaveCount(1);
  await expect(frame.getByRole('button',{name:'Ask AI to complete review'})).toHaveCount(0);
  await frame.getByRole('button',{name:'Show AI instructions'}).click();
  await expect(frame.locator('textarea')).toBeVisible();
  expect(errors).toEqual([]);
});

test('review status, export, printable HTML and explicit deletion',async({page})=>{
  await page.goto('/#synthetic-ui-session'); await selectStudent(page,'8');
  await page.locator('#start-review').click();
  await expect(page.locator('.job h3')).toHaveText('awaiting ai');
  await page.request.get('/test-complete');
  await page.getByRole('button',{name:'Refresh status',exact:true}).click();
  await expect(page.getByRole('button',{name:'Export HTML report'})).toBeVisible();
  const downloadEvent=page.waitForEvent('download');
  await page.getByRole('button',{name:'Export HTML report'}).click();
  const download=await downloadEvent;
  await download.saveAs('/private/tmp/canvas-synthetic-review.html');
  const exportPage=await page.context().newPage();
  await exportPage.goto('file:///private/tmp/canvas-synthetic-review.html');
  await expect(exportPage.locator('h1')).toHaveText('Synthetic Student 8');
  await exportPage.pdf({path:'/private/tmp/canvas-synthetic-review.pdf',format:'A4',printBackground:true});
  await exportPage.screenshot({path:'/private/tmp/canvas-synthetic-review.png',fullPage:true});
  await page.emulateMedia({media:'print'});
  await page.pdf({path:'/private/tmp/canvas-synthetic-dashboard.pdf',format:'A4',printBackground:true});
  await page.emulateMedia({media:'screen'});
  page.on('dialog',d=>d.accept());
  await page.getByRole('button',{name:'Delete local review'}).click();
  await expect(page.locator('.job')).toHaveCount(0);
});
