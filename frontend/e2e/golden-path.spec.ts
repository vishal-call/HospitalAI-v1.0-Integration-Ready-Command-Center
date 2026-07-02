import { test, expect } from '@playwright/test';

test.describe('HospitalAI Golden Path & RBAC E2E Suite', () => {
  
  test('Golden Path E2E Flow', async ({ page }) => {
    // Attach console log listeners
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', err => console.error('BROWSER ERROR:', err.message));

    // 1. Navigate to login and log in as Nurse
    console.log('Navigating to /login...');
    await page.goto('/login');
    await page.locator('#email').waitFor({ state: 'visible' });
    await page.waitForTimeout(2000); // Allow complete React hydration
    
    console.log('Logging in as Nurse...');
    await page.locator('#email').fill('nurse@hospitalai.com');
    await page.locator('#password').fill('password123');
    await page.click('button[type="submit"]');

    // Wait for dashboard redirect
    try {
      await expect(page).toHaveURL('/', { timeout: 4000 });
    } catch (e) {
      const errorText = await page.locator('div.bg-rose-500\\/10').textContent().catch(() => null);
      console.log('LOGIN ERROR ON SCREEN:', errorText);
      throw e;
    }
    console.log('Successfully redirected to Dashboard.');

    // 2. Search for patient "John Stable-Edge" and open Vitals modal
    console.log('Searching for John Stable-Edge...');
    await page.locator('input[placeholder="Search patients..."]').fill('John Stable-Edge');
    
    console.log('Opening Log Vitals modal...');
    await page.click('button:has-text("Log Vitals")');

    // 3. Submit critical vitals (SpO2=85, HR=140, RR=32)
    console.log('Entering critical vitals...');
    await page.locator('input[name="heartRate"]').fill('140');
    await page.locator('input[name="respRate"]').fill('32');
    await page.locator('input[name="spo2"]').fill('85');
    
    console.log('Saving vitals...');
    await page.click('button[type="submit"]:has-text("Save Vitals")');

    // Assert the modal is closed
    await expect(page.locator('text=Log Clinical Vitals')).toBeHidden();

    // 4. Assert that a critical alert appears and a new recommendation populates in the Action Center
    console.log('Asserting critical alert appears in feed...');
    await expect(page.locator('text=displays severe hypoxaemia').first()).toBeVisible({ timeout: 15000 });

    console.log('Asserting recommendation card appears in Action Center...');
    const recCard = page.locator('div:has-text("John Stable-Edge")').filter({ hasText: 'Critical Escalation' }).first();
    await expect(recCard).toBeVisible({ timeout: 15000 });

    // 5. Assert the Nurse is blocked from clicking "Approve" (button disabled)
    console.log('Verifying Nurse is blocked from actioning recommendation...');
    const approveButton = recCard.locator('button:has-text("Approve")');
    await expect(approveButton).toBeDisabled();
    await expect(recCard.locator('text=Clearance to approve')).toBeVisible();

    // 6. Logout
    console.log('Logging out Nurse...');
    await page.click('button[title="Log Out"]');
    await expect(page).toHaveURL('/login');
    await page.waitForTimeout(2000); // Allow complete React hydration

    // 7. Login as Doctor
    console.log('Logging in as Doctor...');
    await page.locator('#email').fill('doctor@hospitalai.com');
    await page.locator('#password').fill('password123');
    await page.click('button[type="submit"]');
    try {
      await expect(page).toHaveURL('/', { timeout: 4000 });
    } catch (e) {
      const errorText = await page.locator('div.bg-rose-500\\/10').textContent().catch(() => null);
      console.log('DOCTOR LOGIN ERROR ON SCREEN:', errorText);
      throw e;
    }
    console.log('Successfully logged in as Doctor.');

    // 8. Doctor approves the pending recommendation
    console.log('Doctor approving recommendation...');
    const docRecCard = page.locator('div:has-text("John Stable-Edge")').filter({ hasText: 'Critical Escalation' }).first();
    await expect(docRecCard).toBeVisible();
    
    const docApproveButton = docRecCard.locator('button:has-text("Approve")');
    await expect(docApproveButton).toBeEnabled();
    await docApproveButton.click();

    // Assert card is removed from queue
    console.log('Verifying recommendation is successfully approved and card is removed...');
    await expect(docRecCard).toBeHidden({ timeout: 10000 });

    // 9. Navigate to /observability and verify the Doctor is blocked (403 Forbidden Access)
    console.log('Attempting to access /observability as Doctor...');
    await page.goto('/observability');
    
    console.log('Verifying Doctor is blocked with 403...');
    await expect(page.locator('h1')).toContainText('403 Forbidden Access');
    await expect(page.locator('text=You do not possess the required administrative clearance')).toBeVisible();
    
    console.log('All Golden Path E2E assertions passed successfully!');
  });
});
