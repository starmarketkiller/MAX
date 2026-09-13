describe("API base URL", () => {
  const originalBackendUrl = process.env.REACT_APP_BACKEND_URL;

  afterEach(() => {
    jest.resetModules();
    if (originalBackendUrl === undefined) delete process.env.REACT_APP_BACKEND_URL;
    else process.env.REACT_APP_BACKEND_URL = originalBackendUrl;
  });

  test("uses exactly /api when REACT_APP_BACKEND_URL is unset", () => {
    delete process.env.REACT_APP_BACKEND_URL;
    jest.isolateModules(() => {
      const { API } = require("./api");
      expect(API).toBe("/api");
    });
  });

  test("appends /api to an explicit backend URL", () => {
    process.env.REACT_APP_BACKEND_URL = "https://example.com";
    jest.isolateModules(() => {
      const { API } = require("./api");
      expect(API).toBe("https://example.com/api");
    });
  });

  test("removes trailing slashes before appending /api", () => {
    process.env.REACT_APP_BACKEND_URL = "https://example.com/";
    jest.isolateModules(() => {
      const { API } = require("./api");
      expect(API).toBe("https://example.com/api");
    });
  });
});
