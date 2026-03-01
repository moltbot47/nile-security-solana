import { render, screen } from "@testing-library/react";
import { KPICard } from "../dashboard/KPICard";

describe("KPICard", () => {
  it("renders title and value", () => {
    render(<KPICard title="Total Scans" value={42} />);
    expect(screen.getByText("Total Scans")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders string value", () => {
    render(<KPICard title="Rate" value="72.2%" />);
    expect(screen.getByText("72.2%")).toBeInTheDocument();
  });

  it("renders subtitle when provided", () => {
    render(<KPICard title="Score" value={85} subtitle="Above average" />);
    expect(screen.getByText("Above average")).toBeInTheDocument();
  });

  it("does not render subtitle when omitted", () => {
    const { container } = render(<KPICard title="Score" value={85} />);
    expect(container.querySelector(".text-xs")).toBeNull();
  });

  it("applies blue color by default", () => {
    const { container } = render(<KPICard title="Test" value={1} />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain("nile");
  });

  it("applies red color when specified", () => {
    const { container } = render(
      <KPICard title="Danger" value={0} color="red" />
    );
    const value = screen.getByText("0");
    expect(value.className).toContain("danger");
  });

  it("shows up trend indicator", () => {
    render(
      <KPICard title="Growth" value={10} subtitle="vs last week" trend="up" />
    );
    expect(screen.getByText("+")).toBeInTheDocument();
  });

  it("shows down trend indicator", () => {
    render(
      <KPICard title="Drop" value={5} subtitle="vs last week" trend="down" />
    );
    expect(screen.getByText("-")).toBeInTheDocument();
  });
});
