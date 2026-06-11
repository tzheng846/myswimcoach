import { fileURLToPath } from "url";
import path from "path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  // A stray lockfile in the user home dir makes Next infer the wrong
  // workspace root — pin it to this app.
  turbopack: {
    root: __dirname,
  },
};

export default nextConfig;
