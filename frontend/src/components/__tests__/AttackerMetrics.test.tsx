import { render, screen } from "@testing-library/react";
import { AttackerMetrics } from "../dashboard/AttackerMetrics";
import type { AttackerKPIs } from "@/lib/types";

const mockData: AttackerKPIs = {
  exploit_success_rate: 0.65,
  avg_time_to_exploit_seconds: 1200,
  attack_vector_distribution: {
    reentrancy: 0.4,
    access_control: 0.3,
    flash_loan: 0.2,
    other: 0.1,
  },
  total_value_at_risk_usd: 50_000_000,
  avg_complexity_score: 4.2,
  zero_day_detection_rate: 0.05,
  time_range: "30d",
};

describe("AttackerMetrics", () => {
  it("renders section title", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(screen.getByText("Attacker-Side KPIs")).toBeInTheDocument();
  });

  it("renders exploit success rate", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(screen.getByText("65.0%")).toBeInTheDocument();
  });

  it("renders time to exploit in minutes", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(screen.getByText("20m")).toBeInTheDocument();
  });

  it("renders value at risk", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(screen.getByText("$50M")).toBeInTheDocument();
  });

  it("renders complexity score", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(screen.getByText("4.2")).toBeInTheDocument();
  });

  it("renders top attack vector", () => {
    render(<AttackerMetrics data={mockData} />);
    const matches = screen.getAllByText("reentrancy");
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("renders attack vector distribution bars", () => {
    render(<AttackerMetrics data={mockData} />);
    expect(
      screen.getByText("Attack Vector Distribution")
    ).toBeInTheDocument();
  });

  it("uses demo data when none provided", () => {
    render(<AttackerMetrics />);
    expect(screen.getByText("72.2%")).toBeInTheDocument();
  });
});
