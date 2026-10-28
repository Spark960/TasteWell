import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tastewell — programming decisions",
  description:
    "Explore venue programming pilots with inspectable Qloo cultural evidence and operator constraints.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full bg-zinc-950 text-zinc-200">{children}</body>
    </html>
  );
}
