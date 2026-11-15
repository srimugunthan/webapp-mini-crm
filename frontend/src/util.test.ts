import { dateInputToEpoch, epochToDateInput, fmtTs, fullName, stepStage } from "./util";
import { qs } from "./api";

const stages = [{ id: 1 }, { id: 2 }, { id: 3 }];

describe("stepStage", () => {
  it("moves forward and back", () => {
    expect(stepStage(stages, 1, 1)?.id).toBe(2);
    expect(stepStage(stages, 3, -1)?.id).toBe(2);
  });
  it("stops at the ends", () => {
    expect(stepStage(stages, 3, 1)).toBeNull();
    expect(stepStage(stages, 1, -1)).toBeNull();
  });
  it("from no stage, next goes to first and back is unavailable", () => {
    expect(stepStage(stages, null, 1)?.id).toBe(1);
    expect(stepStage(stages, null, -1)).toBeNull();
  });
  it("handles empty pipelines", () => expect(stepStage([], null, 1)).toBeNull());
});

describe("dates", () => {
  it("round-trips a date input via local noon", () => {
    const ts = dateInputToEpoch("2024-10-01")!;
    expect(epochToDateInput(ts)).toBe("2024-10-01");
    expect(new Date(ts * 1000).getHours()).toBe(12);
  });
  it("empty values", () => {
    expect(dateInputToEpoch("")).toBeNull();
    expect(fmtTs(null)).toBe("—");
    expect(epochToDateInput(null)).toBe("");
  });
  it("fullName", () => {
    expect(fullName({ first_name: "A", last_name: "Rao" })).toBe("A Rao");
    expect(fullName({ first_name: "", last_name: "" })).toBe("(no name)");
  });
});

describe("qs", () => {
  it("drops empty values and encodes", () => {
    expect(qs({ q: "a b", x: "", y: null, z: false, n: 0, t: true })).toBe("?q=a+b&n=0&t=true");
    expect(qs({})).toBe("");
  });
});
