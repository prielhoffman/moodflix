import {
  fetchMe,
  fetchWatchlist,
  login,
  recommendShows,
} from "./moodflixApi";

function jsonResponse(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: () => "application/json",
    },
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

describe("moodflixApi", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  test("recommendShows sends POST to /recommend with provided payload", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    const payload = { age: 25, mood: "chill", binge_preference: "binge" };
    await recommendShows(payload);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/recommend",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      })
    );
  });

  test("fetchMe includes Authorization header when token exists", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: 1, email: "u@example.com" }));
    vi.stubGlobal("fetch", fetchMock);
    localStorage.setItem("access_token", "token-123");

    await fetchMe();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer token-123");
  });

  test("login stores token and watchlist endpoint uses it", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ access_token: "jwt-token", token_type: "bearer" }))
      .mockResolvedValueOnce(jsonResponse({ watchlist: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await login("person@example.com", "pw123456");
    await fetchWatchlist();

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "http://127.0.0.1:8000/auth/login",
      expect.objectContaining({
        method: "POST",
      })
    );

    const [, watchlistOptions] = fetchMock.mock.calls[1];
    expect(watchlistOptions.headers.Authorization).toBe("Bearer jwt-token");
  });
});
