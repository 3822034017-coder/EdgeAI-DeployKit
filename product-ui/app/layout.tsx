import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'EdgeAI DeployKit Control Plane',
  description: 'Product-grade WebUI for EdgeAI-DeployKit model deployment pipeline.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
