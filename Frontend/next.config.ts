import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL
          ? `${process.env.NEXT_PUBLIC_API_URL}/:path*`
          : 'http://localhost:5000/api/:path*', // Fallback to localhost for development
      },
    ];
  },
};

export default nextConfig;