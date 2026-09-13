// @vitest-environment jsdom
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
vi.mock("recharts", async () => {
  const actual = await vi.importActual<typeof import("recharts")>("recharts");
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
  };
});
beforeAll(() => {
  window.scrollTo = vi.fn();
});
afterEach(cleanup);
const nav = () => within(document.querySelector("nav")!);
describe("Pulse frontend demo", () => {
  it("completes the opportunity-to-approved campaign flow and preserves edits", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      screen.getAllByRole("button", { name: "View Opportunity" })[0],
    );
    expect(screen.getByRole("heading", { name: "Sunday Reset" })).toBeTruthy();
    await user.click(
      screen.getAllByRole("button", { name: "Build This Campaign" })[0],
    );
    expect(
      screen.getByText(/3 things I do Sunday night/, {
        selector: ".hook-field p",
      }),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "Edit" }));
    const hook = screen.getByLabelText("The hook");
    await user.clear(hook);
    await user.type(hook, "A fresh start for Monday.");
    await user.click(screen.getByRole("button", { name: "Save edits" }));
    await user.click(
      screen.getByRole("button", { name: "Approve Campaign" }),
    );
    expect(
      screen
        .getByRole("button", { name: "Campaign Approved" })
        .hasAttribute("disabled"),
    ).toBe(true);
    await user.click(
      nav().getByRole("button", { name: "Campaigns" }),
    );
    expect(
      screen.getByRole("heading", {
        name: "Sunday Reset — Hydra Electrolyte Mix",
      }),
    ).toBeTruthy();
    await user.click(screen.getByRole("button", { name: "View campaign" }));
    expect(screen.getByText("A fresh start for Monday.")).toBeTruthy();
    await user.click(nav().getByRole("button", { name: "Agent Activity" }));
    expect(
      screen.getByRole("heading", { name: "Campaign approved" }),
    ).toBeTruthy();
  });
  it("opens every top navigation page, dismisses and restores opportunities, and scans mock trends", async () => {
    const user = userEvent.setup();
    render(<App />);
    for (const page of [
      "Audience",
      "Trends",
      "Campaigns",
      "Agent Activity",
      "Integrations",
      "Overview",
    ]) {
      await user.click(nav().getByRole("button", { name: page }));
      expect(
        screen.getByRole("heading", {
          level: 1,
          name: page === "Overview" ? "What should Pulse work on?" : page,
        }),
      ).toBeTruthy();
    }
    await user.click(nav().getByRole("button", { name: /Opportunities/ }));
    await user.click(
      screen.getAllByRole("button", { name: "Dismiss" })[0],
    );
    expect(screen.queryByRole("heading", { name: "Sunday Reset" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Restore dismissed" }));
    expect(screen.getByRole("heading", { name: "Sunday Reset" })).toBeTruthy();
    await user.click(
      nav().getByRole("button", { name: "Trends" }),
    );
    await user.click(screen.getByRole("button", { name: "Scan trends" }));
    expect(screen.getByText("Desk-to-Gym Ritual")).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Emerging" }),
    );
    expect(screen.queryByText("Cold Plunge")).toBeNull();
  });
  it("toggles mock integrations and answers Ask Pulse without requests", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);
    const user = userEvent.setup();
    render(<App />);
    await user.click(nav().getByRole("button", { name: "Integrations" }));
    await user.click(screen.getByRole("button", { name: "Connect HubSpot" }));
    expect(
      screen.getByRole("button", { name: "Disconnect HubSpot" }),
    ).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Disconnect HubSpot" }),
    );
    expect(
      screen.getByRole("button", { name: "Connect HubSpot" }),
    ).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Ask Pulse" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Why does Sunday Reset fit Hydra?" }),
    );
    expect(screen.getByText(/Sunday Reset matches 92%/)).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Explore Sunday Reset" }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("heading", { name: "Sunday Reset" })).toBeTruthy();
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
  it("regenerates creative and moves rejected campaigns into the Rejected tab", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      screen.getAllByRole("button", { name: "View Opportunity" })[0],
    );
    await user.click(
      screen.getAllByRole("button", { name: "Build This Campaign" })[0],
    );
    await user.click(screen.getByRole("button", { name: "Regenerate" }));
    expect(
      screen.getByText("My Monday starts with what I do on Sunday.", {
        selector: ".hook-field p",
      }),
    ).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Reject" }),
    );
    expect(
      screen.getByRole("heading", {
        name: "Sunday Reset — Hydra Electrolyte Mix",
      }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /Rejected 1/ })).toBeTruthy();
  });
});


it('uses the main composer and retains one navigation menu', async () => {
  const user = userEvent.setup();
  render(<App />);
  expect(screen.getAllByRole('navigation')).toHaveLength(1);
  expect(screen.queryByRole('group', { name: 'Explore marketing tools' })).toBeNull();
  await user.click(screen.getByRole('button', { name: 'Research trends' }));
  const command = screen.getByLabelText('Give Pulse a direction') as HTMLTextAreaElement;
  expect(command.value).toBe('What is trending among college students?');
  await user.click(screen.getByRole('button', { name: 'Ask Pulse' }));
  expect(screen.getByRole('button', { name: 'Working…' }).hasAttribute('disabled')).toBe(true);
  expect(await screen.findByText(/Sunday Reset is up 218%/)).toBeTruthy();
  expect(screen.getByText('Pulse / response ready')).toBeTruthy();
  await user.click(screen.getByRole('button', { name: 'Review opportunities' }));
  expect(screen.getByRole('heading', { name: 'Marketing opportunities' })).toBeTruthy();
});
