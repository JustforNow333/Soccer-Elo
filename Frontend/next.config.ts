import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://192.168.1.102:5000/api/:path*', // Use your backend's LAN IP here
      },
    ];
  },
};

export default nextConfig;