import { render, screen } from "@testing-library/react";
import { DefenderMetrics } from "../dashboard/DefenderMetrics";
import type { DefenderKPIs } from "@/lib/types";

const mockData: DefenderKPIs = {
  detection_recall: 0.85,
  patch_success_rate: 0.72,
  false_positive_rate: 0.08,
  avg_time_to_detection_seconds: 300,
  avg_time_to_patch_seconds: 1800,
  audit_coverage_score: 0.9,
  security_posture_score: 0.88,
  time_range: "30d",
};

describe("DefenderMetrics", () => {
  it("renders section title", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("Defender-Side KPIs")).toBeInTheDocument();
  });

  it("renders detection recall", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("85.0%")).toBeInTheDocument();
  });

  it("renders patch success rate", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("72.0%")).toBeInTheDocument();
  });

  it("renders false positive rate", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("8.0%")).toBeInTheDocument();
  });

  it("renders time to detection in minutes", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("5m")).toBeInTheDocument();
  });

  it("renders time to patch in minutes", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("30m")).toBeInTheDocument();
  });

  it("renders audit coverage", () => {
    render(<DefenderMetrics data={mockData} />);
    expect(screen.getByText("90.0%")).toBeInTheDocument();
  });

  it("uses demo data when none provided", () => {
    render(<DefenderMetrics />);
    expect(screen.getByText("68.0%")).toBeInTheDocument();
  });
});
