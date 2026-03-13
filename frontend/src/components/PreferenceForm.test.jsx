import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PreferenceForm from "./PreferenceForm";

describe("PreferenceForm", () => {
  test("submits required fields", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<PreferenceForm onSubmit={onSubmit} />);

    await user.selectOptions(screen.getByLabelText(/^mood$/i), "happy");
    await user.click(screen.getByRole("button", { name: /get recommendations/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      mood: "happy",
      binge_preference: "binge",
      preferred_genres: [],
      watching_context: "alone",
      query: "",
    });
  });

  test("submits advanced preferences when selected", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<PreferenceForm onSubmit={onSubmit} />);

    await user.click(screen.getByText(/advanced preferences/i));
    await user.click(screen.getByLabelText("action"));
    await user.click(screen.getByLabelText("drama"));
    await user.selectOptions(screen.getByLabelText(/^episode length$/i), "long");
    await user.selectOptions(screen.getByLabelText(/^watching context$/i), "family");
    await user.click(screen.getByRole("button", { name: /get recommendations/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith({
      mood: "chill",
      binge_preference: "binge",
      preferred_genres: ["action", "drama"],
      episode_length_preference: "long",
      watching_context: "family",
      query: "",
    });
  });

  test("omits any/null-like optional selections", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();

    render(<PreferenceForm onSubmit={onSubmit} />);

    await user.click(screen.getByText(/advanced preferences/i));
    await user.selectOptions(screen.getByLabelText(/^episode length$/i), "any");
    await user.click(screen.getByRole("button", { name: /get recommendations/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const payload = onSubmit.mock.calls[0][0];

    expect(payload).toMatchObject({
      mood: "chill",
      binge_preference: "binge",
      preferred_genres: [],
      watching_context: "alone",
    });
    expect(payload).not.toHaveProperty("episode_length_preference");
  });
});
