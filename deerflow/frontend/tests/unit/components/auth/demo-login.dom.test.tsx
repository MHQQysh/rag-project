import { afterEach, describe, expect, it, rs } from "@rstest/core";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";

import { DemoLogin } from "@/components/auth/demo-login";

afterEach(() => {
  cleanup();
  rs.restoreAllMocks();
});

describe("demo login", () => {
  it("does not offer disabled demo access", async () => {
    rs.spyOn(globalThis, "fetch").mockResolvedValue(
      Response.json({ enabled: false }),
    );
    const { container } = render(<DemoLogin />);
    await act(async () => {
      await Promise.resolve();
    });
    expect(container.textContent).toBe("");
  });

  it("enters without sending credentials and reloads the workspace", async () => {
    const fetch = rs
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({ enabled: true }))
      .mockResolvedValueOnce(Response.json({ needs_setup: false }));
    const assign = rs
      .spyOn(window.location, "assign")
      .mockImplementation(() => undefined);
    render(<DemoLogin />);
    fireEvent.click(await screen.findByRole("button", { name: "进入演示" }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(fetch).toHaveBeenLastCalledWith("/api/v1/auth/login/demo", {
      method: "POST",
      credentials: "include",
    });
    expect(assign).toHaveBeenCalledWith("/workspace/chats/new");
    expect(screen.getByText(/访客共享/)).toBeTruthy();
  });

  it("shows a retryable error when entry fails", async () => {
    rs.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(Response.json({ enabled: true }))
      .mockResolvedValueOnce(new Response(null, { status: 503 }));
    render(<DemoLogin />);
    fireEvent.click(await screen.findByRole("button", { name: "进入演示" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button").getAttribute("disabled")).toBeNull();
  });
});
