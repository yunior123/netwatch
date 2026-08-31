import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "netwatch — wifi activity",
  description: "Live, local-only wifi activity monitoring panel",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
