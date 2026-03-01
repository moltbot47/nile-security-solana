import { render, screen } from "@testing-library/react";
import { ScoreResult } from "../scan/ScoreResult";
import type { SolanaScanResult } from "@/lib/types";

const mockResult: SolanaScanResult = {
  address: "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
  analysis_type: "program",
  total_score: 82.5,
  grade: "A",
  scores: { name: 90, image: 75, likeness: 80, essence: 85 },
  details: {},
  exploit_matches: [],
};

describe("ScoreResult", () => {
  it("renders scan result header", () => {
    render(<ScoreResult result={mockResult} />);
    expect(screen.getByText("Scan Result")).toBeInTheDocument();
  });

  it("renders address", () => {
    render(<ScoreResult result={mockResult} />);
    expect(
      screen.getByText("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    ).toBeInTheDocument();
  });

  it("renders analysis type badge", () => {
    render(<ScoreResult result={mockResult} />);
    expect(screen.getByText("program")).toBeInTheDocument();
  });

  it("renders grade in banner", () => {
    render(<ScoreResult result={mockResult} />);
    expect(screen.getByText("NILE Grade:")).toBeInTheDocument();
    expect(screen.getByText("(82.5/100)")).toBeInTheDocument();
  });

  it("renders all four dimension bars", () => {
    render(<ScoreResult result={mockResult} />);
    expect(
      screen.getByText("Name (Identity & Reputation)")
    ).toBeInTheDocument();
    expect(screen.getByText("Image (Security Posture)")).toBeInTheDocument();
    expect(screen.getByText("Likeness (Pattern Matching)")).toBeInTheDocument();
    expect(screen.getByText("Essence (Code Quality)")).toBeInTheDocument();
  });

  it("renders exploit match count when present", () => {
    const withMatches: SolanaScanResult = {
      ...mockResult,
      exploit_matches: [
        {
          pattern_id: "p1",
          name: "Reentrancy",
          category: "access",
          severity: "high",
          confidence: 0.9,
          cwe: "CWE-123",
          indicators_matched: ["ind1"],
        },
        {
          pattern_id: "p2",
          name: "Flash Loan",
          category: "defi",
          severity: "medium",
          confidence: 0.7,
          cwe: null,
          indicators_matched: [],
        },
      ],
    };
    render(<ScoreResult result={withMatches} />);
    expect(screen.getByText(/2 exploit patterns matched/)).toBeInTheDocument();
  });

  it("does not show exploit count when empty", () => {
    render(<ScoreResult result={mockResult} />);
    expect(screen.queryByText(/exploit pattern/)).toBeNull();
  });

  it("renders token analysis type", () => {
    const tokenResult = { ...mockResult, analysis_type: "token" as const };
    render(<ScoreResult result={tokenResult} />);
    expect(screen.getByText("token")).toBeInTheDocument();
  });
});
