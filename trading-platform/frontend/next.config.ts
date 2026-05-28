import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://127.0.0.1:8000";

    return [
      {
        source: "/dashboard/:path+",
        destination: `${backendUrl}/dashboard/:path+`,
      },
      {
        source: "/monitoring/:path+",
        destination: `${backendUrl}/monitoring/:path+`,
      },
    ];
  },
};

export default nextConfig;
