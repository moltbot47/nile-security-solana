import { render, screen } from "@testing-library/react";
import { PersonCard } from "../persons/PersonCard";
import type { PersonListItem } from "@/lib/types";

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

const basePerson: PersonListItem = {
  id: "1",
  display_name: "LeBron James",
  slug: "lebron-james",
  avatar_url: null,
  verification_level: "premium",
  category: "athlete",
  nile_total_score: 92,
  token_symbol: "BRON",
  token_price_usd: 14.5,
  token_market_cap_usd: 2_500_000,
};

describe("PersonCard", () => {
  it("renders display name", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("LeBron James")).toBeInTheDocument();
  });

  it("renders verification badge", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("premium")).toBeInTheDocument();
  });

  it("renders category", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("athlete")).toBeInTheDocument();
  });

  it("links to person detail page", () => {
    render(<PersonCard person={basePerson} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/persons/lebron-james");
  });

  it("renders token symbol when present", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("$BRON")).toBeInTheDocument();
  });

  it("renders first letter when no avatar", () => {
    render(<PersonCard person={basePerson} />);
    expect(screen.getByText("L")).toBeInTheDocument();
  });

  it("renders avatar image when URL provided", () => {
    const withAvatar = {
      ...basePerson,
      avatar_url: "https://example.com/avatar.jpg",
    };
    render(<PersonCard person={withAvatar} />);
    const img = screen.getByAltText("LeBron James");
    expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg");
  });

  it("hides token section when no symbol", () => {
    const noToken = { ...basePerson, token_symbol: null };
    render(<PersonCard person={noToken} />);
    expect(screen.queryByText(/\$/)).toBeNull();
  });
});
