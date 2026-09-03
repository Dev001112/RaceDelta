import { describe, it, expect } from "vitest";
import { getTeamKey, getTeamColor, getDriverAbbreviation, TEAM_COLORS } from "./teamMeta";

describe("getTeamKey", () => {
  it("resolves the names the API actually sends", () => {
    expect(getTeamKey("Red Bull Racing")).toBe("red_bull");
    expect(getTeamKey("Racing Bulls")).toBe("rb");
    expect(getTeamKey("Kick Sauber")).toBe("sauber");
    expect(getTeamKey("Aston Martin")).toBe("aston_martin");
    expect(getTeamKey("mclaren")).toBe("mclaren");
  });

  it("falls back to unknown", () => {
    expect(getTeamKey("")).toBe("unknown");
    expect(getTeamKey(null)).toBe("unknown");
    expect(getTeamKey("Brabham")).toBe("unknown");
    expect(getTeamColor("Brabham")).toBe(TEAM_COLORS.unknown);
  });
});

describe("getDriverAbbreviation", () => {
  it("prefers the code, else the surname", () => {
    expect(getDriverAbbreviation("Lando Norris", "nor")).toBe("NOR");
    expect(getDriverAbbreviation("Lando Norris")).toBe("NOR");
    expect(getDriverAbbreviation("Kimi")).toBe("KIM");
    expect(getDriverAbbreviation("")).toBe("DRV");
  });
});
