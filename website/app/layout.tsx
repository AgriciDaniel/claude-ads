import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meta Performance Analyzer",
  description:
    "Diagnose your Meta Ads and organic posts with a 50-check AI audit. Get your health score, quick wins, and actionable insights in 60 seconds.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
