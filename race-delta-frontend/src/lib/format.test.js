import { describe, it, expect } from "vitest";
import { formatDuration } from "./format";

describe("formatDuration", () => {
  it("shows the winner's race time as h:mm:ss.sss", () => {
    expect(formatDuration(7484.859, 1)).toBe("2:04:44.859");
    expect(formatDuration(1825.318, 1)).toBe("30:25.318");
    expect(formatDuration(null, 1)).toBe("FINISHED");
  });

  it("shows everyone else's gap to the leader", () => {
    expect(formatDuration(7496.395, 2, 11.536)).toBe("+11.536s");
    expect(formatDuration(0, 8, "+1 Lap")).toBe("+1 Lap");
    expect(formatDuration(0, 9, "1 Lap")).toBe("1 Lap");
    expect(formatDuration(0, 3, "15.906")).toBe("+15.906");
    expect(formatDuration(0, 3, 0)).toBe("FINISHED");
  });
});
