import type { NextConfig } from "next";

// The FastAPI backend. Server components call it directly; the browser goes through the
// /api rewrite below, so client code stays same-origin (no CORS, no backend URL in the bundle).
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },
};

export default nextConfig;
