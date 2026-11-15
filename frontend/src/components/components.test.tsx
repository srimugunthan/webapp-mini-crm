import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StageNoteModal from "./StageNoteModal";
import Board from "./Board";
import type { Member, Stage } from "../types";

describe("StageNoteModal", () => {
  it("Enter saves the note, Esc skips it", async () => {
    const onDone = vi.fn();
    render(<StageNoteModal label="Move A" onDone={onDone} onCancel={() => {}} />);
    const input = screen.getByLabelText("Stage note");
    await userEvent.type(input, "called him{Enter}");
    expect(onDone).toHaveBeenLastCalledWith("called him");
    await userEvent.type(input, "{Escape}");
    expect(onDone).toHaveBeenLastCalledWith(undefined);
  });
});

const stages: Stage[] = [{ id: 1, group_id: 1, name: "A", position: 0, is_final: false }, { id: 2, group_id: 1, name: "B", position: 1, is_final: false }];
const mem = (id: number, stage: number | null): Member => ({
  contact_id: id, first_name: `P${id}`, last_name: "X", company: "", position: "", linkedin_url: "", last_visited_at: null, last_messaged_at: null,
  stage_id: stage, stage_name: null, stage_is_final: 0, stage_changed_at: null, next_follow_up_at: null, days_in_stage: 2,
});

describe("Board", () => {
  it("shows one column per stage with cards, and the dropdown alternative moves a card", async () => {
    const onMove = vi.fn();
    render(<Board stages={stages} members={[mem(1, 1), mem(2, 2)]} onMove={onMove} />);
    expect(screen.getByTestId("col-A")).toHaveTextContent("P1 X");
    expect(screen.getByTestId("col-B")).toHaveTextContent("P2 X");
    await userEvent.selectOptions(screen.getByLabelText("Stage for P1 X"), "2");
    expect(onMove).toHaveBeenCalledWith(expect.objectContaining({ contact_id: 1 }), 2);
  });
  it("shows a No stage column only when someone has no stage", () => {
    render(<Board stages={stages} members={[mem(1, null)]} onMove={() => {}} />);
    expect(screen.getByTestId("col-No stage")).toBeInTheDocument();
  });
});
