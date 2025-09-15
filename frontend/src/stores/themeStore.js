import { create } from "zustand";

export const useThemeStore = create((set) => ({
  theme: "dark",

  toggleTheme: () =>
    set((state) => {
      const newTheme = state.theme === "dark" ? "light" : "dark";

      if (newTheme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }

      return { theme: newTheme };
    }),

  setTheme: (theme) =>
    set(() => {
      if (theme === "dark") {
        document.documentElement.classList.add("dark");
      } else {
        document.documentElement.classList.remove("dark");
      }

      return { theme };
    }),
}));
