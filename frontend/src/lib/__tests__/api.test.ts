import { api } from "../api";

// Mock global fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

beforeEach(() => {
  mockFetch.mockReset();
});

function mockJsonResponse(data: unknown, status = 200) {
  mockFetch.mockResolvedValueOnce({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
  });
}

function mockErrorResponse(status: number) {
  mockFetch.mockResolvedValueOnce({
    ok: false,
    status,
    json: () => Promise.resolve({ detail: "error" }),
  });
}

describe("api.contracts", () => {
  it("list fetches /api/v1/contracts", async () => {
    mockJsonResponse([{ id: "1", name: "Test" }]);
    const result = await api.contracts.list();
    expect(result).toEqual([{ id: "1", name: "Test" }]);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/contracts");
  });

  it("get fetches by id", async () => {
    mockJsonResponse({ id: "abc" });
    await api.contracts.get("abc");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/contracts/abc");
  });

  it("nileHistory fetches score history", async () => {
    mockJsonResponse([]);
    await api.contracts.nileHistory("abc");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/contracts/abc/nile-history"
    );
  });
});

describe("api.benchmarks", () => {
  it("baselines fetches /api/v1/benchmarks/baselines", async () => {
    mockJsonResponse([{ agent: "gpt-5", score_pct: 31.9 }]);
    const result = await api.benchmarks.baselines();
    expect(result).toEqual([{ agent: "gpt-5", score_pct: 31.9 }]);
  });

  it("list fetches /api/v1/benchmarks", async () => {
    mockJsonResponse([]);
    await api.benchmarks.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/benchmarks");
  });
});

describe("api.agents", () => {
  it("leaderboard fetches with default limit", async () => {
    mockJsonResponse([]);
    await api.agents.leaderboard();
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/agents/leaderboard?limit=25"
    );
  });

  it("list filters by status", async () => {
    mockJsonResponse([]);
    await api.agents.list("active");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/agents?status=active");
  });

  it("list without status omits param", async () => {
    mockJsonResponse([]);
    await api.agents.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/agents");
  });
});

describe("api.scans", () => {
  it("list fetches with default params", async () => {
    mockJsonResponse([]);
    await api.scans.list();
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/scans?limit=50");
  });

  it("list filters by status", async () => {
    mockJsonResponse([]);
    await api.scans.list("running");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/scans?limit=50&status=running"
    );
  });
});

describe("api.persons", () => {
  it("trending fetches with limit", async () => {
    mockJsonResponse([]);
    await api.persons.trending(10);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/persons/trending?limit=10"
    );
  });

  it("list with search param", async () => {
    mockJsonResponse([]);
    await api.persons.list({ search: "lebron" });
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/persons?search=lebron"
    );
  });
});

describe("api.soulTokens", () => {
  it("marketOverview fetches correctly", async () => {
    mockJsonResponse({ total_tokens: 10 });
    const result = await api.soulTokens.marketOverview();
    expect(result).toEqual({ total_tokens: 10 });
  });

  it("list uses sort param", async () => {
    mockJsonResponse([]);
    await api.soulTokens.list("volume");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/soul-tokens?sort=volume&limit=50"
    );
  });
});

describe("api.scan", () => {
  it("solana posts address", async () => {
    mockJsonResponse({ address: "test", total_score: 85 });
    await api.scan.solana("test_address");
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/scan/solana", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ program_address: "test_address" }),
    });
  });
});

describe("error handling", () => {
  it("throws on non-ok response", async () => {
    mockErrorResponse(404);
    await expect(api.contracts.list()).rejects.toThrow("API error: 404");
  });

  it("throws on 500", async () => {
    mockErrorResponse(500);
    await expect(api.agents.leaderboard()).rejects.toThrow("API error: 500");
  });
});
