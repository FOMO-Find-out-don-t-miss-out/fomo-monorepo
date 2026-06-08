/** @type {import('next').NextConfig} */

// NEXT_PUBLIC_* vars are baked into the bundle at build time.
// Fail loudly here so CI catches a missing build arg before the image ships.
if (process.env.NODE_ENV === "production" && !process.env.NEXT_PUBLIC_API_URL) {
  throw new Error(
    "NEXT_PUBLIC_API_URL is required for production builds.\n" +
    "Pass it as a Docker build arg:\n" +
    "  --build-arg NEXT_PUBLIC_API_URL=https://api.staging.fomo-lab.org/api/v1"
  );
}

const nextConfig = {
  output: 'standalone',
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
