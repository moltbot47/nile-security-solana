import { useWalletStore } from "../wallet";

describe("useWalletStore", () => {
  beforeEach(() => {
    useWalletStore.setState({ network: "devnet" });
  });

  it("defaults to devnet", () => {
    expect(useWalletStore.getState().network).toBe("devnet");
  });

  it("setNetwork updates to mainnet-beta", () => {
    useWalletStore.getState().setNetwork("mainnet-beta");
    expect(useWalletStore.getState().network).toBe("mainnet-beta");
  });

  it("setNetwork updates back to devnet", () => {
    useWalletStore.getState().setNetwork("mainnet-beta");
    useWalletStore.getState().setNetwork("devnet");
    expect(useWalletStore.getState().network).toBe("devnet");
  });
});
