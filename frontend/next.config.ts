import type { NextConfig } from "next";

const rawBasePath = process.env.NEXT_BASE_PATH?.trim();
const basePath = rawBasePath && rawBasePath !== "/" ? rawBasePath : undefined;

const nextConfig: NextConfig = {
  basePath,
  assetPrefix: basePath,
  trailingSlash: true,
};

export default nextConfig;
