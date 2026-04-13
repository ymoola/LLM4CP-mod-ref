import './globals.css';

import { AppHeader } from '@/components/app-header';
import { AuthGate } from '@/components/auth-gate';
import { AuthProvider } from '@/components/auth-provider';
import { AppQueryProvider } from '@/lib/query-client';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppQueryProvider>
          <AuthProvider>
            <div className="min-h-screen">
              <AppHeader />
              <main className="mx-auto max-w-6xl px-6 py-8">
                <AuthGate>{children}</AuthGate>
              </main>
            </div>
          </AuthProvider>
        </AppQueryProvider>
      </body>
    </html>
  );
}
