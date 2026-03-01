import { useDashboard } from "../dashboard";

// Mock the api module
vi.mock("@/lib/api", () => ({
  api: {
    contracts: {
      list: vi.fn(),
    },
    agents: {
      list: vi.fn(),
      leaderboard: vi.fn(),
    },
    events: {
      history: vi.fn(),
    },
    kpis: {
      attacker: vi.fn(),
      defender: vi.fn(),
    },
  },
}));

// Import after mocking
const { api } = await import("@/lib/api");

describe("useDashboard store", () => {
  beforeEach(() => {
    // Reset store state between tests
    useDashboard.setState({
      contracts: [],
      agents: [],
      leaderboard: [],
      events: [],
      attackerKPIs: null,
      defenderKPIs: null,
      loading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  it("initializes with empty state", () => {
    const state = useDashboard.getState();
    expect(state.contracts).toEqual([]);
    expect(state.agents).toEqual([]);
    expect(state.loading).toBe(false);
    expect(state.error).toBeNull();
  });

  it("fetchContracts sets contracts on success", async () => {
    const mockContracts = [{ id: "1", name: "Test" }];
    vi.mocked(api.contracts.list).mockResolvedValueOnce(mockContracts as never);
    await useDashboard.getState().fetchContracts();
    expect(useDashboard.getState().contracts).toEqual(mockContracts);
  });

  it("fetchContracts sets error on failure", async () => {
    vi.mocked(api.contracts.list).mockRejectedValueOnce(new Error("fail"));
    await useDashboard.getState().fetchContracts();
    expect(useDashboard.getState().error).toBe("Failed to load contracts");
  });

  it("fetchAgents sets agents on success", async () => {
    const mockAgents = [{ id: "a1", name: "Agent1" }];
    vi.mocked(api.agents.list).mockResolvedValueOnce(mockAgents as never);
    await useDashboard.getState().fetchAgents();
    expect(useDashboard.getState().agents).toEqual(mockAgents);
  });

  it("fetchAgents sets error on failure", async () => {
    vi.mocked(api.agents.list).mockRejectedValueOnce(new Error("fail"));
    await useDashboard.getState().fetchAgents();
    expect(useDashboard.getState().error).toBe("Failed to load agents");
  });

  it("fetchLeaderboard sets leaderboard on success", async () => {
    const mockLeaderboard = [{ id: "a1", name: "Top Agent", total_points: 100 }];
    vi.mocked(api.agents.leaderboard).mockResolvedValueOnce(mockLeaderboard as never);
    await useDashboard.getState().fetchLeaderboard();
    expect(useDashboard.getState().leaderboard).toEqual(mockLeaderboard);
  });

  it("fetchEvents sets events on success", async () => {
    const mockEvents = [{ id: "e1", event_type: "scan.completed" }];
    vi.mocked(api.events.history).mockResolvedValueOnce(mockEvents as never);
    await useDashboard.getState().fetchEvents();
    expect(useDashboard.getState().events).toEqual(mockEvents);
  });

  it("addEvent prepends event and caps at 100", () => {
    const event = { id: "new", event_type: "test" } as never;
    useDashboard.getState().addEvent(event);
    expect(useDashboard.getState().events[0]).toEqual(event);
    expect(useDashboard.getState().events.length).toBe(1);
  });

  it("addEvent caps at 100 events", () => {
    // Fill with 100 events
    const events = Array.from({ length: 100 }, (_, i) => ({
      id: `e${i}`,
      event_type: "test",
    }));
    useDashboard.setState({ events: events as never });

    const newEvent = { id: "new", event_type: "latest" } as never;
    useDashboard.getState().addEvent(newEvent);
    const state = useDashboard.getState();
    expect(state.events.length).toBe(100);
    expect(state.events[0]).toEqual(newEvent);
  });

  it("fetchAttackerKPIs sets data on success", async () => {
    const kpis = { exploit_success_rate: 0.5 };
    vi.mocked(api.kpis.attacker).mockResolvedValueOnce(kpis as never);
    await useDashboard.getState().fetchAttackerKPIs();
    expect(useDashboard.getState().attackerKPIs).toEqual(kpis);
  });

  it("fetchDefenderKPIs sets data on success", async () => {
    const kpis = { detection_recall: 0.8 };
    vi.mocked(api.kpis.defender).mockResolvedValueOnce(kpis as never);
    await useDashboard.getState().fetchDefenderKPIs();
    expect(useDashboard.getState().defenderKPIs).toEqual(kpis);
  });
});
