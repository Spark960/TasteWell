import type { Metadata } from "next";
import "@fontsource/dm-sans/400.css";
import "@fontsource/dm-sans/500.css";
import "@fontsource/dm-sans/600.css";
import "@fontsource/dm-sans/700.css";
import "@fontsource/newsreader/500.css";
import "@fontsource/newsreader/600.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tastewell — programming decisions",
  description:
    "Explore venue programming pilots with inspectable Qloo cultural evidence and operator constraints.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full">{children}</body>
    </html>
  );
}
