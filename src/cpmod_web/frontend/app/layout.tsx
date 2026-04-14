import './globals.css';

import type { Metadata } from 'next';

import { AppHeader } from '../components/app-header';
import { AuthGate } from '../components/auth-gate';
import { AuthProvider } from '../components/auth-provider';
import { AppQueryProvider } from '../lib/query-client';

export const metadata: Metadata = {
  title: 'ConstraintMod',
  description: 'Constraint programming model modification with an auditable workflow.',
  icons: {
    icon: [
      { url: '/favicon.png?v=3', type: 'image/png', sizes: '256x256' },
    ],
    shortcut: '/favicon.png?v=3',
    apple: '/apple-icon.png?v=3',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppQueryProvider>
          <AuthProvider>
            <div className="app-shell min-h-screen">
              <AppHeader />
              <main className="app-main mx-auto w-full max-w-[118rem] px-4 pb-10 pt-6 sm:px-6 lg:px-8">
                <AuthGate>{children}</AuthGate>
              </main>
            </div>
          </AuthProvider>
        </AppQueryProvider>
      </body>
    </html>
  );
}
