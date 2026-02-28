import { describe, expect, it } from "vitest";
import { formatPercent, gradeColor, scoreToGrade } from "../utils";

describe("scoreToGrade", () => {
  it("returns A+ for score >= 90", () => {
    expect(scoreToGrade(90)).toBe("A+");
    expect(scoreToGrade(95)).toBe("A+");
    expect(scoreToGrade(100)).toBe("A+");
  });

  it("returns A for score 80-89", () => {
    expect(scoreToGrade(80)).toBe("A");
    expect(scoreToGrade(89)).toBe("A");
  });

  it("returns B for score 70-79", () => {
    expect(scoreToGrade(70)).toBe("B");
    expect(scoreToGrade(79)).toBe("B");
  });

  it("returns C for score 60-69", () => {
    expect(scoreToGrade(60)).toBe("C");
    expect(scoreToGrade(69)).toBe("C");
  });

  it("returns D for score 50-59", () => {
    expect(scoreToGrade(50)).toBe("D");
    expect(scoreToGrade(59)).toBe("D");
  });

  it("returns F for score < 50", () => {
    expect(scoreToGrade(0)).toBe("F");
    expect(scoreToGrade(49)).toBe("F");
  });
});

describe("gradeColor", () => {
  it("returns safe color for A+ and A", () => {
    expect(gradeColor("A+")).toBe("text-security-safe");
    expect(gradeColor("A")).toBe("text-security-safe");
  });

  it("returns yellow for B", () => {
    expect(gradeColor("B")).toBe("text-yellow-400");
  });

  it("returns warning for C", () => {
    expect(gradeColor("C")).toBe("text-security-warning");
  });

  it("returns orange for D", () => {
    expect(gradeColor("D")).toBe("text-orange-500");
  });

  it("returns danger for F and unknown", () => {
    expect(gradeColor("F")).toBe("text-security-danger");
    expect(gradeColor("X")).toBe("text-security-danger");
  });
});

describe("formatPercent", () => {
  it("formats decimal to percentage string", () => {
    expect(formatPercent(0.5)).toBe("50.0%");
    expect(formatPercent(1)).toBe("100.0%");
    expect(formatPercent(0.123)).toBe("12.3%");
  });

  it("handles zero", () => {
    expect(formatPercent(0)).toBe("0.0%");
  });

  it("handles small values", () => {
    expect(formatPercent(0.001)).toBe("0.1%");
  });
});
