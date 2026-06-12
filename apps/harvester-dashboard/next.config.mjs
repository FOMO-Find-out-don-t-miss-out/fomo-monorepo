/** @type {import('next').NextConfig} */

// NEXT_PUBLIC_* vars are baked into the bundle at build time.
// Fail loudly here so CI catches missing build args before the image ships.
if (process.env.NODE_ENV === "production") {
  const required = [
    "NEXT_PUBLIC_API_URL",
    "NEXT_PUBLIC_KEYCLOAK_URL",
    "NEXT_PUBLIC_KEYCLOAK_REALM",
    "NEXT_PUBLIC_KEYCLOAK_CLIENT_ID",
  ];
  for (const v of required) {
    if (!process.env[v]) {
      throw new Error(
        `${v} is required for production builds.\n` +
        `Pass it as a Docker build arg: --build-arg ${v}=<value>`
      );
    }
  }
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
