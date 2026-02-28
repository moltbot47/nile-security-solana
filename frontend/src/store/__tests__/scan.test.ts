import { afterEach, describe, expect, it, vi } from "vitest";
import { useScan } from "../scan";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    scan: {
      solana: vi.fn(),
    },
  },
}));

describe("useScan store", () => {
  afterEach(() => {
    // Reset store state between tests
    useScan.setState({
      address: "",
      scanning: false,
      result: null,
      error: null,
      history: [],
    });
    vi.restoreAllMocks();
  });

  it("initializes with empty state", () => {
    const state = useScan.getState();
    expect(state.address).toBe("");
    expect(state.scanning).toBe(false);
    expect(state.result).toBeNull();
    expect(state.error).toBeNull();
    expect(state.history).toEqual([]);
  });

  it("setAddress updates address", () => {
    useScan.getState().setAddress("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
    expect(useScan.getState().address).toBe("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");
  });

  it("submitScan sets scanning state and result on success", async () => {
    const { api } = await import("@/lib/api");
    const mockResult = {
      address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
      analysis_type: "program",
      total_score: 85,
      grade: "A",
      scores: { name: 80, image: 90, likeness: 85, essence: 87 },
      details: {},
      exploit_matches: [],
    };
    vi.mocked(api.scan.solana).mockResolvedValue(mockResult as never);

    const submitPromise = useScan.getState().submitScan("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA");

    // During scan, scanning should be true
    expect(useScan.getState().scanning).toBe(true);

    await submitPromise;

    const state = useScan.getState();
    expect(state.scanning).toBe(false);
    expect(state.result).toEqual(mockResult);
    expect(state.error).toBeNull();
    expect(state.history).toHaveLength(1);
  });

  it("submitScan sets error on failure", async () => {
    const { api } = await import("@/lib/api");
    vi.mocked(api.scan.solana).mockRejectedValue(new Error("Network error"));

    await useScan.getState().submitScan("bad-address");

    const state = useScan.getState();
    expect(state.scanning).toBe(false);
    expect(state.result).toBeNull();
    expect(state.error).toBe("Network error");
  });

  it("clearResult resets result and error", () => {
    useScan.setState({ result: { address: "test" } as never, error: "old error" });
    useScan.getState().clearResult();

    expect(useScan.getState().result).toBeNull();
    expect(useScan.getState().error).toBeNull();
  });
});
