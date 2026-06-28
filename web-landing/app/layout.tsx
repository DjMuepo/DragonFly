import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Eye Platform',
  description: 'AI-guided 3D design and printable object sharing.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
