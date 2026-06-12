import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    env: {
      NEXT_PUBLIC_API_URL: 'http://localhost:8000/api/v1',
      NEXT_PUBLIC_KEYCLOAK_URL: 'http://localhost:8080',
      NEXT_PUBLIC_KEYCLOAK_REALM: 'test-realm',
      NEXT_PUBLIC_KEYCLOAK_CLIENT_ID: 'test-client',
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
    },
  },
});
