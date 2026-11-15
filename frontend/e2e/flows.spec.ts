import { expect, test, Page } from "@playwright/test";
import path from "node:path";

const FIXTURE = path.resolve(process.cwd(), "../backend/tests/fixtures/Connections.csv");

async function importFixture(page: Page) {
  await page.goto("/import");
  await page.getByLabel("CSV to add").setInputFiles(FIXTURE);
  await page.getByRole("button", { name: "Upload and add to contacts" }).click();
  await expect(page.getByTestId("import-summary")).toContainText("4 new");
}

test.describe.serial("end to end", () => {
  test("import -> group -> add members -> stage move with history", async ({ page }) => {
    await expect(async () => {
      await page.goto("/");
      await expect(page.getByTestId("health")).toContainText("backend ok");
    }).toPass();
    await importFixture(page);
    await page.goto("/");
    await expect(page.getByText("Contacts (4)")).toBeVisible();

    // create a group with the preselected Starter pipeline
    await page.goto("/groups");
    await page.getByLabel("Group name").fill("Prospects");
    await expect(page.getByLabel("Pipeline")).toHaveValue("1");
    await page.getByRole("button", { name: "Create group" }).click();
    await expect(page.getByRole("link", { name: "Prospects" })).toBeVisible();

    // add all contacts from the contacts list
    await page.goto("/");
    await page.getByLabel("Select all on page").check();
    await page.getByLabel("Target group").selectOption({ label: "Prospects" });
    await page.getByRole("button", { name: "Add to group" }).click();
    await expect(page.getByText("Added 4")).toBeVisible();

    await page.goto("/groups");
    await page.getByRole("link", { name: "Prospects" }).click();
    await expect(page.getByTestId("chips")).toContainText("Connected 4");

    // dropdown move, skip the note with Escape
    await page.getByLabel("Stage for Asha Rao", { exact: true }).selectOption({ label: "Reached out" });
    await page.getByLabel("Stage note").press("Escape");
    await expect(page.getByTestId("chips")).toContainText("Reached out 1");
    // next button with a note saved by Enter
    await page.getByLabel("Next stage for Asha Rao").click();
    await page.getByLabel("Stage note").fill("replied");
    await page.getByLabel("Stage note").press("Enter");
    await expect(page.getByTestId("chips")).toContainText("In conversation 1");
    // moving into the final stage asks for confirmation
    page.once("dialog", (d) => d.accept());
    await page.getByLabel("Next stage for Asha Rao").click();
    await page.getByLabel("Stage note").press("Escape");
    await expect(page.getByTestId("chips")).toContainText("Closed 1");
    // final stage members are hidden by default, shown with the toggle
    await expect(page.getByTestId("chips")).toContainText("All 4");
    await expect(page.getByLabel("Stage for Asha Rao", { exact: true })).toHaveCount(0);
    // URL-backed checkbox updates in a router transition, so click then assert (check() verifies too early)
    await page.getByLabel("show final-stage members").click();
    await expect(page.getByLabel("show final-stage members")).toBeChecked();
    await expect(page.getByLabel("Stage for Asha Rao", { exact: true })).toBeVisible();

    // visit tracking: clicking the link goes through /go/{id} (LinkedIn itself is stubbed)
    await page.context().route(/linkedin\.com/, (r) => r.fulfill({ status: 200, body: "stub linkedin" }));
    const [popup] = await Promise.all([page.context().waitForEvent("page"), page.getByRole("link", { name: /asha-rao/ }).click()]);
    await popup.waitForLoadState();
    expect(popup.url()).toContain("linkedin.com/in/asha-rao");
    await popup.close();
    await expect.poll(async () => (await (await page.request.get("/api/contacts?q=Asha")).json()).items[0].last_visited_at).not.toBeNull();

    // no "did you message?" prompt on refocus
    await page.evaluate(() => window.dispatchEvent(new Event("focus")));
    await expect(page.getByRole("dialog")).toHaveCount(0);

    // history visible in the contact drawer
    await page.goto("/");
    await page.getByRole("button", { name: "Asha Rao" }).click();
    const drawer = page.getByLabel("Contact detail");
    await expect(drawer).toContainText("Connected → Reached out");
    await expect(drawer).toContainText("replied");
  });

  test("bulk set stage: preview, apply, undo", async ({ page }) => {
    await page.goto("/groups");
    await page.getByLabel("Group name").fill("Bulk");
    await page.getByRole("button", { name: "Create group" }).click();
    await page.getByRole("link", { name: "Bulk" }).click();
    await page.getByRole("button", { name: "Bulk set stage" }).click();
    const csv = "URL,Stage\nhttps://linkedin.com/in/Priya-Nair/,In conversation\nhttps://www.linkedin.com/in/lilei,Reached out\nhttps://www.linkedin.com/in/nobody,Closed\nhttps://www.linkedin.com/in/unal-celik,Bogus\n";
    await page.getByLabel("Bulk CSV").setInputFiles({ name: "b.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
    await page.getByRole("button", { name: "Preview" }).click();
    const pv = page.getByTestId("bulk-preview");
    await expect(pv).toContainText("0 will be moved");
    await expect(pv).toContainText("2 not in this group yet (will be added)");
    await expect(pv).toContainText("1 URLs not found");
    await expect(pv).toContainText("1 rows with unknown stage");
    await expect(page.getByRole("link", { name: "Download problem rows" })).toBeVisible();
    await page.getByRole("button", { name: "Apply" }).click();
    await expect(page.getByText("Done: 0 moved, 2 added")).toBeVisible();
    await page.getByRole("button", { name: "Close", exact: true }).click();
    await expect(page.getByTestId("chips")).toContainText("In conversation 1");
    await expect(page.getByTestId("chips")).toContainText("Reached out 1");
    await page.getByRole("button", { name: "Undo last bulk change" }).click();
    await expect(page.getByText("Undone: 0 restored, 2 removed.")).toBeVisible();
    await expect(page.getByTestId("chips")).toContainText("All 0");
  });

  test("board view: drag a card to another column; no-pipeline group hides stage UI", async ({ page }) => {
    await page.goto("/groups");
    await page.getByRole("link", { name: "Prospects" }).click();
    await page.getByRole("button", { name: "Board", exact: true }).click();
    await expect(page.getByTestId("col-Connected")).toContainText("Priya Nair");
    await page.getByTestId("card-" + (await page.getByTestId("col-Connected").locator("[data-testid^=card-]").first().getAttribute("data-testid"))!.replace("card-", ""))
      .dragTo(page.getByTestId("col-Reached out"));
    await page.getByLabel("Stage note").press("Escape");
    await expect(page.getByTestId("col-Reached out").locator("[data-testid^=card-]")).toHaveCount(1);
    await expect(page.getByTestId("chips")).toContainText("Reached out 1");

    await page.goto("/groups");
    await page.getByLabel("Group name").fill("Plain");
    await page.getByLabel("Pipeline").selectOption("none");
    await page.getByRole("button", { name: "Create group" }).click();
    await page.getByRole("link", { name: "Plain" }).click();
    await expect(page.getByTestId("chips")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Board", exact: true })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Bulk set stage" })).toBeDisabled();
  });

  test("add people to a group: CSV on create, then Add members (search and CSV)", async ({ page }) => {
    await page.goto("/groups");
    await page.getByLabel("Group name").fill("FromCsv");
    await page.getByLabel("Pipeline").selectOption("none");
    const csv = "URL\nhttps://www.linkedin.com/in/asha-rao\nhttps://www.linkedin.com/in/lilei\nhttps://www.linkedin.com/in/ghost\n";
    await page.getByLabel("Members CSV").setInputFiles({ name: "m.csv", mimeType: "text/csv", buffer: Buffer.from(csv) });
    await page.getByRole("button", { name: "Create group" }).click();
    await expect(page.getByText("with 2 people from the CSV (1 URLs were not found")).toBeVisible();
    await page.getByRole("link", { name: "FromCsv" }).click();
    await expect(page.getByText("Page 1 of 1 (2 members)")).toBeVisible();

    await page.getByRole("button", { name: "Add members" }).click();
    await page.getByLabel("Search contacts to add").fill("Priya");
    await page.getByLabel("Add Priya Nair").check();
    await page.getByRole("button", { name: /Add 1 selected/ }).click();
    await expect(page.getByText("Added 1.")).toBeVisible();
    await page.getByRole("button", { name: "Upload CSV" }).click();
    await page.getByLabel("Members CSV").setInputFiles({ name: "m2.csv", mimeType: "text/csv", buffer: Buffer.from("URL\nhttps://www.linkedin.com/in/unal-celik\nhttps://www.linkedin.com/in/lilei\n") });
    await page.getByRole("button", { name: "Preview" }).click();
    await expect(page.getByTestId("members-csv-preview")).toContainText("1 will be added · 1 already in the group");
    await page.getByRole("button", { name: "Add 1 people" }).click();
    await expect(page.getByText("Added 1 people to FromCsv.")).toBeVisible();
    await page.getByRole("button", { name: "Close", exact: true }).click();
    await expect(page.getByText("Page 1 of 1 (4 members)")).toBeVisible();
  });

  test("filter, select and act on the selection: export selected / matching, mark messaged", async ({ page }) => {
    await page.goto("/?company=Co");
    await expect(page.getByTestId("selection-bar")).toContainText("Tick rows");
    await expect(page.getByRole("link", { name: /Export all \d+ matching CSV/ })).toBeVisible();
    await page.getByLabel("Select all on page").check();
    const bar = page.getByTestId("selection-bar");
    await expect(bar).toContainText("selected");
    const [dl] = await Promise.all([page.waitForEvent("download"), bar.getByRole("button", { name: /Export \d+ selected CSV/ }).click()]);
    expect(dl.suggestedFilename()).toBe("selected-contacts.csv");
    await bar.getByRole("button", { name: /Mark \d+ messaged/ }).click();
    await expect(page.getByText(/Marked \d+ as messaged/)).toBeVisible();
    await expect(page.getByTestId("selection-bar")).toContainText("Tick rows"); // selection cleared
  });

  test("group page: tick members, rows highlight, export selected, mark messaged, remove", async ({ page }) => {
    await page.goto("/groups");
    await page.getByRole("link", { name: "FromCsv" }).click();
    const bar = page.getByTestId("selection-bar");
    await expect(bar).toContainText("Tick members");
    const first = page.getByRole("row").nth(1);
    await first.getByRole("checkbox").check();
    await expect(first).toHaveClass(/selected/);
    await page.getByRole("row").nth(2).getByRole("checkbox").check();
    await expect(bar).toContainText("2 selected");
    const [dl] = await Promise.all([page.waitForEvent("download"), bar.getByRole("button", { name: /Export 2 selected CSV/ }).click()]);
    expect(dl.suggestedFilename()).toBe("FromCsv-selected.csv");
    await bar.getByRole("button", { name: /Mark 2 messaged/ }).click();
    await expect(page.getByText("Marked 2 as messaged.")).toBeVisible();
    await expect(bar).toContainText("Tick members");
    await page.getByRole("row").nth(1).getByRole("checkbox").check();
    page.once("dialog", (d) => d.accept());
    await bar.getByRole("button", { name: /Remove 1 from group/ }).click();
    await expect(page.getByText("Removed 1 from the group.")).toBeVisible();
    await expect(page.getByText("(3 members)")).toBeVisible();
  });

  test("fresh import: needs the typed confirmation, then replaces everything", async ({ page }) => {
    await page.goto("/import");
    await page.getByLabel("CSV for fresh import").setInputFiles({ name: "new.csv", mimeType: "text/csv",
      buffer: Buffer.from("First Name,Last Name,URL,Email Address,Company,Position,Connected On\nZed,One,https://www.linkedin.com/in/zed1,,NewCo,Eng,01 Jan 2025\n") });
    await page.getByRole("button", { name: "Upload and Fresh import" }).click();
    const dialog = page.getByRole("dialog", { name: "Replace all your data?" });
    await expect(dialog).toContainText("overwrites your database");
    await expect(dialog).toContainText(/\d+ contacts, \d+ groups/);
    const go = dialog.getByRole("button", { name: "Delete everything and import" });
    await expect(go).toBeDisabled();
    await dialog.getByLabel("Type RESET to confirm").fill("reset");
    await expect(go).toBeDisabled(); // case matters
    await dialog.getByLabel("Type RESET to confirm").fill("RESET");
    await go.click();
    await expect(page.getByTestId("import-summary")).toContainText("Fresh import done");
    await expect(page.getByTestId("import-summary")).toContainText("1 new");
    await page.goto("/");
    await expect(page.getByText("Contacts (1)")).toBeVisible();
    await page.goto("/groups");
    await expect(page.getByText("No groups yet.")).toBeVisible();
    await page.goto("/pipelines");
    await expect(page.getByRole("row", { name: /Starter/ })).toContainText("Connected → Reached out → In conversation → Closed (final)");
    await expect(page.getByRole("row")).toHaveCount(2); // header + the re-created Starter only
  });

  test("restore from a .sqlite backup: preview, typed confirmation, data comes back", async ({ page }) => {
    // the previous test left exactly 1 contact; take a backup of that state
    const backup = await (await page.request.get("/api/backup")).body();
    await page.goto("/import");
    await page.getByLabel("CSV to add").setInputFiles({ name: "more.csv", mimeType: "text/csv",
      buffer: Buffer.from("First Name,Last Name,URL,Email Address,Company,Position,Connected On\nA,B,https://www.linkedin.com/in/ab,,Co,E,01 Jan 2025\nC,D,https://www.linkedin.com/in/cd,,Co,E,01 Jan 2025\n") });
    await page.getByRole("button", { name: "Upload and add to contacts" }).click();
    await expect(page.getByTestId("import-summary")).toContainText("2 new");
    await page.goto("/");
    await expect(page.getByText("Contacts (3)")).toBeVisible();

    await page.goto("/import");
    await page.getByLabel("SQLite backup file").setInputFiles({ name: "backup.sqlite", mimeType: "application/octet-stream", buffer: backup });
    await page.getByRole("button", { name: "Upload and restore database" }).click();
    const dialog = page.getByRole("dialog", { name: "Replace your database with this backup?" });
    await expect(dialog).toContainText("overwrites your database");
    await expect(dialog).toContainText("contains 1 contacts");
    await expect(dialog).toContainText("3 contacts"); // current data that will be replaced
    const go = dialog.getByRole("button", { name: "Replace database" });
    await expect(go).toBeDisabled();
    await dialog.getByLabel("Type RESTORE to confirm").fill("RESET");
    await expect(go).toBeDisabled();
    await dialog.getByLabel("Type RESTORE to confirm").fill("RESTORE");
    await go.click();
    await expect(page.getByTestId("restore-summary")).toContainText("1 contacts");
    await page.goto("/");
    await expect(page.getByText("Contacts (1)")).toBeVisible();

    // a file that is not a database is rejected with a clear message and nothing changes
    await page.goto("/import");
    await page.getByLabel("SQLite backup file").setInputFiles({ name: "notes.sqlite", mimeType: "text/plain", buffer: Buffer.from("hello") });
    await page.getByRole("button", { name: "Upload and restore database" }).click();
    await expect(page.getByRole("alert")).toContainText("not a SQLite database");
  });

  test("group page: Mark messaged per row (now and a past date) and no sideways scrolling at laptop widths", async ({ page }) => {
    // self-contained setup through the API (earlier tests restored/reset the data)
    const rows = ["Ada,Lovelace", "Grace,Hopper", "Alan,Turing"].map((n, i) => `${n},https://www.linkedin.com/in/layout${i},,Analytical Engines Ltd,Principal Research Engineer and Mathematician,01 Jan 2024`);
    await page.request.post("/api/import", { multipart: { file: { name: "l.csv", mimeType: "text/csv", buffer: Buffer.from("First Name,Last Name,URL,Email Address,Company,Position,Connected On\n" + rows.join("\n") + "\n") } } });
    const ids: number[] = (await (await page.request.get("/api/contacts?company=Analytical%20Engines")).json()).items.map((c: { id: number }) => c.id);
    const gid = (await (await page.request.post("/api/groups", { data: { name: "Layout", template_id: 1 } })).json()).id;
    await page.request.post(`/api/groups/${gid}/members`, { data: { contact_ids: ids } });
    await page.goto(`/groups/${gid}`);
    const row = page.getByRole("row").nth(1);
    const name = (await row.getByRole("cell").nth(1).innerText()).trim();
    await row.getByRole("button", { name: "Mark messaged" }).click();
    await expect(row.getByRole("cell").nth(6)).not.toHaveText("—"); // Messaged column now has a date
    await row.getByLabel(`Messaged date for ${name}`).fill("2024-10-01");
    await row.getByRole("button", { name: "Set" }).click();
    await expect(row.getByRole("cell").nth(6)).toContainText("Oct");
    await expect(row.getByRole("cell").nth(6)).toContainText("24");

    for (const width of [1280, 1366, 1536]) {
      await page.setViewportSize({ width, height: 800 });
      for (const url of ["/", "/groups"]) {
        await page.goto(url === "/" ? "/" : "/groups");
        if (url === "/groups") await page.goto(`/groups/${gid}`);
        await expect(page.locator("table.contacts")).toBeVisible();
        const over = await page.locator(".table-wrap").first().evaluate((el) => el.scrollWidth - el.clientWidth);
        expect(over, `${url} at ${width}px overflows by ${over}px`).toBeLessThanOrEqual(1);
      }
    }
  });

  test("contacts: boolean search incl. the Group box, syntax errors, help panel", async ({ page }) => {
    // self-contained data through the API
    const rows = [["Asha", "Rao", "Google", "Data Scientist"], ["Ben", "Kumar", "Google", "Product Manager"], ["Chen", "Li", "Acme", "Data Engineer"], ["Dee", "Nair", "Acme", "Recruiter"]]
      .map(([f, l, c, p], i) => `${f},${l},https://www.linkedin.com/in/bool${i},,${c},${p},01 Jan 2024`);
    await page.request.post("/api/import", { multipart: { file: { name: "b.csv", mimeType: "text/csv", buffer: Buffer.from("First Name,Last Name,URL,Email Address,Company,Position,Connected On\n" + rows.join("\n") + "\n") } } });
    const ids: Record<string, number> = {};
    for (const c of (await (await page.request.get("/api/contacts?limit=500")).json()).items) ids[c.first_name] = c.id;
    const mk = async (name: string, who: string[]) => {
      const g = (await (await page.request.post("/api/groups", { data: { name } })).json()).id;
      await page.request.post(`/api/groups/${g}/members`, { data: { contact_ids: who.map((w) => ids[w]) } });
    };
    await mk("BoolHR", ["Dee", "Ben"]);
    await mk("BoolML", ["Asha", "Chen"]);
    await mk("BoolHot", ["Asha", "Dee", "Ben"]);

    await page.goto("/?q=Asha%20OR%20Ben%20OR%20Chen%20OR%20Dee"); // restrict to the four test people
    const count = page.getByRole("heading", { name: /Contacts \(\d+\)/ });
    await expect(count).toContainText("(4)");
    await page.getByLabel("Group filter").fill("BoolHR OR BoolML");
    await expect(count).toContainText("(4)");
    await page.getByLabel("Group filter").fill("BoolHot AND NOT BoolML");
    await expect(count).toContainText("(2)");
    await expect(page.getByRole("button", { name: "Ben Kumar" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Dee Nair" })).toBeVisible();
    await page.getByLabel("Search", { exact: true }).fill("data AND (google OR acme) NOT recruiter");
    await page.getByLabel("Group filter").fill("");
    await expect(count).toContainText("(2)"); // Asha and Chen

    await page.getByLabel("Search", { exact: true }).fill("(data");
    await expect(page.getByText("Search syntax error: missing “)”.")).toBeVisible();
    await page.getByLabel("Search", { exact: true }).fill("company:acme AND group:BoolHR");
    await expect(page.getByText("Search syntax error")).toHaveCount(0);
    await expect(count).toContainText("(1)"); // Dee

    await expect(page.getByTestId("search-help")).toHaveCount(0);
    await page.getByRole("button", { name: "Search help" }).click();
    await expect(page.getByTestId("search-help")).toContainText("Boolean search");
    // the selection export honours the same filter
    await page.getByLabel("Select all on page").check();
    const [dl] = await Promise.all([page.waitForEvent("download"), page.getByTestId("selection-bar").getByRole("button", { name: /Export 1 selected CSV/ }).click()]);
    expect(dl.suggestedFilename()).toBe("selected-contacts.csv");
  });

  test("import: optional group name (people I follow) and a plain import with no group", async ({ page }) => {
    const header = "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n";
    const mk = (n: string, who: string[]) => ({ name: n, mimeType: "text/csv", buffer: Buffer.from(header + who.map((w, i) => `${w},X,https://www.linkedin.com/in/${n}${w}${i},,FollowCo,Eng,01 Jan 2025`).join("\n") + "\n") });
    const before = (await (await page.request.get("/api/contacts?limit=1")).json()).total as number;

    await page.goto("/import");
    await page.getByLabel("CSV to add").setInputFiles(mk("follow", ["Una", "Vic"]));
    await page.getByLabel("Group name for this upload").fill("Following");
    await page.getByRole("button", { name: "Upload and add to contacts" }).click();
    const sum = page.getByTestId("import-summary");
    await expect(sum).toContainText("2 new");
    await expect(sum).toContainText("Following");
    await expect(sum).toContainText("was created");
    await expect(sum).toContainText("2 people added");

    // a second file with no group name: just contacts, no new group
    await page.getByLabel("CSV to add").setInputFiles(mk("conn", ["Wes"]));
    await expect(page.getByLabel("Group name for this upload")).toHaveValue(""); // cleared after the upload
    await page.getByRole("button", { name: "Upload and add to contacts" }).click();
    await expect(page.getByTestId("import-summary")).toContainText("1 new");
    await expect(page.getByTestId("import-summary")).not.toContainText("Group ");

    // Contacts shows everyone; the Group box finds just the followed people
    await page.goto("/");
    await expect(page.getByRole("heading", { name: /Contacts \(\d+\)/ })).toContainText(`(${before + 3})`);
    await page.getByLabel("Group filter").fill("Following");
    await expect(page.getByRole("heading", { name: /Contacts \(\d+\)/ })).toContainText("(2)");

    // the group name suggestions include existing groups, and reusing the name reuses the group
    await page.goto("/import");
    await expect(page.locator("#existing-groups option[value=Following]")).toHaveCount(1);
    await page.getByLabel("CSV to add").setInputFiles(mk("again", ["Xia"]));
    await page.getByLabel("Group name for this upload").fill("following");
    await page.getByRole("button", { name: "Upload and add to contacts" }).click();
    await expect(page.getByTestId("import-summary")).toContainText("already existed");
  });
});
