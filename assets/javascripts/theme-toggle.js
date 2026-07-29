(() => {
  const storageKey = "codex-radar.theme";
  const windowNamePrefix = "codex-radar-theme:";

  function readStoredTheme() {
    try {
      const value = window.localStorage.getItem(storageKey);
      if (value === "default" || value === "slate") return value;
    } catch (_) {
      // file:// may deny access to localStorage.
    }

    if (window.name.startsWith(windowNamePrefix)) {
      const value = window.name.slice(windowNamePrefix.length);
      if (value === "default" || value === "slate") return value;
    }
    return null;
  }

  function storeTheme(scheme) {
    try {
      window.localStorage.setItem(storageKey, scheme);
    } catch (_) {
      // window.name keeps the choice for navigation in the same file:// tab.
    }

    if (!window.name || window.name.startsWith(windowNamePrefix)) {
      window.name = `${windowNamePrefix}${scheme}`;
    }
  }

  function applyTheme(input, persist) {
    if (!input) return;

    const attributes = ["media", "scheme", "primary", "accent"];
    for (const attribute of attributes) {
      const value = input.getAttribute(`data-md-color-${attribute}`);
      if (value) document.body.setAttribute(`data-md-color-${attribute}`, value);
    }

    input.checked = true;
    document.documentElement.style.colorScheme =
      input.getAttribute("data-md-color-scheme") === "slate" ? "dark" : "light";

    const form = input.closest('[data-md-component="palette"]');
    if (form) {
      for (const label of form.querySelectorAll("label[for]")) {
        label.hidden = label.htmlFor === input.id;
      }
    }

    if (persist) storeTheme(input.getAttribute("data-md-color-scheme"));
  }

  function initializeThemeToggle() {
    const inputs = Array.from(document.querySelectorAll('input[name="__palette"]'));
    if (inputs.length < 2) return;

    for (const input of inputs) {
      input.addEventListener("change", () => applyTheme(input, true));
    }

    const stored = readStoredTheme();
    const preferred = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "slate"
      : "default";
    const initial = inputs.find(
      input => input.getAttribute("data-md-color-scheme") === (stored || preferred),
    ) || inputs[0];
    applyTheme(initial, false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeThemeToggle, { once: true });
  } else {
    initializeThemeToggle();
  }
})();
