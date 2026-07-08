import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// ponytail: GH Pages project site only; local/docker builds keep base "/"
const base = process.env.GITHUB_PAGES === "1" ? "/et-hackathon/" : "/"

export default defineConfig({
  base,
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
})
