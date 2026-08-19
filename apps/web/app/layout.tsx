import type { Metadata } from 'next'
import localFont from 'next/font/local'
import './globals.css'

const appFont = localFont({
  src: './fonts/GeistVF.woff',
})

export const metadata: Metadata = {
  title: 'Doc-XRay | AI Document Intelligence',
  description: 'AI-Powered Visual Document Intelligence Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // We force dark mode on the body element to match the premium SaaS aesthetic
  return (
    <html lang="en" className="dark">
      <body className={`${appFont.className} min-h-screen bg-background text-foreground flex flex-col`}>
        <header className="h-14 flex items-center px-6 border-b border-white/5 glass sticky top-0 z-50">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-white text-black flex items-center justify-center font-bold text-xs">
              DX
            </div>
            <span className="font-semibold tracking-tight">Doc-XRay</span>
          </div>
          <nav className="ml-auto flex gap-6 text-sm text-muted-foreground">
            <a href="/" className="hover:text-foreground transition-colors">Upload</a>
            <a href="/history" className="hover:text-foreground transition-colors">History</a>
          </nav>
        </header>
        <main className="flex-1 flex flex-col">
          {children}
        </main>
      </body>
    </html>
  )
}
