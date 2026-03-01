import { render, screen } from "@testing-library/react";
import { NileScoreGauge } from "../dashboard/NileScoreGauge";

describe("NileScoreGauge", () => {
  it("renders A+ grade for score >= 90", () => {
    render(<NileScoreGauge score={95} />);
    expect(screen.getByText("A+")).toBeInTheDocument();
    expect(screen.getByText("95.0")).toBeInTheDocument();
  });

  it("renders A grade for score 80-89", () => {
    render(<NileScoreGauge score={85} />);
    expect(screen.getByText("A")).toBeInTheDocument();
  });

  it("renders B grade for score 70-79", () => {
    render(<NileScoreGauge score={75} />);
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("renders F grade for score < 50", () => {
    render(<NileScoreGauge score={30} />);
    expect(screen.getByText("F")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<NileScoreGauge score={80} label="Security" />);
    expect(screen.getByText("Security")).toBeInTheDocument();
  });

  it("does not render label when omitted", () => {
    const { container } = render(<NileScoreGauge score={80} />);
    const labels = container.querySelectorAll("span.text-sm");
    expect(labels.length).toBe(0);
  });

  it("renders SVG circle element", () => {
    const { container } = render(<NileScoreGauge score={80} />);
    const circles = container.querySelectorAll("circle");
    expect(circles.length).toBe(2); // background + progress
  });

  it("applies small size class", () => {
    const { container } = render(<NileScoreGauge score={80} size="sm" />);
    expect(container.querySelector(".w-24")).toBeTruthy();
  });
});
