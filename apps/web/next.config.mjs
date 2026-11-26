/** @type {import('next').NextConfig} */
const nextConfig = {
  agentRules: false,
  output: "standalone",
  async rewrites() {
    const backend = process.env.RAI_DEMO_INTERNAL_API;
    if (!backend) return [];

    return [
      { source: "/health", destination: `${backend}/health` },
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` }
    ];
  }
};

export default nextConfig;
