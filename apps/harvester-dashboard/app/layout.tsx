import type { Metadata, Viewport } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import { Toaster } from 'sonner'
import { Providers } from '@/components/providers/query-client-provider'
import { AuthProvider } from '@/components/providers/auth-provider'
import './globals.css'

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono" });

export const metadata: Metadata = {
  title: 'FOMO - Event Moderation Dashboard',
  description: 'High-performance event moderation dashboard for FOMO SaaS',
}

export const viewport: Viewport = {
  themeColor: '#0d0d12',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <Providers>
          <AuthProvider>
            {children}
          </AuthProvider>
          <Toaster theme="dark" position="bottom-right" />
          <Analytics />
        </Providers>
      </body>
    </html>
  )
}
