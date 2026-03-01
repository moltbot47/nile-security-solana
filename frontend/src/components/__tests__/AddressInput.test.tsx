import { render, screen, fireEvent } from "@testing-library/react";
import { AddressInput } from "../scan/AddressInput";

// Valid Solana address (base58, 32-44 chars)
const VALID_ADDRESS = "11111111111111111111111111111111";
const ETH_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678";

describe("AddressInput", () => {
  it("renders input and scan button", () => {
    render(<AddressInput onSubmit={vi.fn()} />);
    expect(screen.getByPlaceholderText(/Paste a Solana/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Scan/ })).toBeInTheDocument();
  });

  it("validates empty submission", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: /Scan/ }));
    // Button is disabled when input is empty, so onSubmit should not be called
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects Ethereum addresses", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    const input = screen.getByPlaceholderText(/Paste a Solana/);
    fireEvent.change(input, { target: { value: ETH_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /Scan/ }));
    expect(screen.getByText(/Ethereum address/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects invalid base58", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    const input = screen.getByPlaceholderText(/Paste a Solana/);
    fireEvent.change(input, { target: { value: "too-short" } });
    fireEvent.click(screen.getByRole("button", { name: /Scan/ }));
    expect(screen.getByText(/Invalid Solana address/)).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits valid address", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    const input = screen.getByPlaceholderText(/Paste a Solana/);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /Scan/ }));
    expect(onSubmit).toHaveBeenCalledWith(VALID_ADDRESS);
  });

  it("submits on Enter key", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    const input = screen.getByPlaceholderText(/Paste a Solana/);
    fireEvent.change(input, { target: { value: VALID_ADDRESS } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSubmit).toHaveBeenCalledWith(VALID_ADDRESS);
  });

  it("shows disabled state", () => {
    render(<AddressInput onSubmit={vi.fn()} disabled />);
    expect(screen.getByPlaceholderText(/Paste a Solana/)).toBeDisabled();
    expect(screen.getByRole("button", { name: /Scanning/ })).toBeDisabled();
  });

  it("clears error on input change", () => {
    const onSubmit = vi.fn();
    render(<AddressInput onSubmit={onSubmit} />);
    const input = screen.getByPlaceholderText(/Paste a Solana/);
    // Trigger an error first
    fireEvent.change(input, { target: { value: ETH_ADDRESS } });
    fireEvent.click(screen.getByRole("button", { name: /Scan/ }));
    expect(screen.getByText(/Ethereum address/)).toBeInTheDocument();
    // Type to clear the error
    fireEvent.change(input, { target: { value: "a" } });
    expect(screen.queryByText(/Ethereum address/)).not.toBeInTheDocument();
  });
});
