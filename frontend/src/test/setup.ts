import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";

import { server } from "@/test/msw-server";
import { TOKEN_STORAGE_KEY } from "@/lib/api";

// Recharts' ResponsiveContainer needs ResizeObserver, which jsdom does not
// implement. Provide a no-op shim so charts mount without throwing.
class ResizeObserverStub {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}
if (typeof globalThis.ResizeObserver === "undefined") {
  globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});

beforeEach(() => {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
});
