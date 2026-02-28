import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingState } from "../common/LoadingState";

describe("LoadingState", () => {
  it("renders card variant by default", () => {
    const { container } = render(<LoadingState />);
    expect(container.querySelector(".rounded-xl")).toBeTruthy();
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("renders gauge variant", () => {
    const { container } = render(<LoadingState variant="gauge" />);
    expect(container.querySelector(".rounded-full")).toBeTruthy();
  });

  it("renders table variant with correct number of rows", () => {
    const { container } = render(<LoadingState variant="table" rows={3} />);
    const rows = container.querySelectorAll(".flex.gap-4");
    expect(rows.length).toBe(3);
  });

  it("renders inline variant", () => {
    const { container } = render(<LoadingState variant="inline" />);
    expect(container.querySelector("span.inline-block")).toBeTruthy();
  });
});
