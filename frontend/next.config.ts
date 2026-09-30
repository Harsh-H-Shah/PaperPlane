import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // GitHub Pages needs a static export; the Docker image uses standalone.
  output: process.env.NEXT_OUTPUT === 'export' ? 'export' : 'standalone',
};

export default nextConfig;
