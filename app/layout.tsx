import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Noto_Sans_JP } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { AppShell } from "@/components/shell/app-shell";
import "./globals.css";

/* Geist carries Latin and every numeral; Noto Sans JP picks up the CJK
   glyphs Geist has no coverage for. The stack in globals.css orders them
   so figures always render in Geist Mono. */
const notoJP = Noto_Sans_JP({
  variable: "--font-noto-jp",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Ledger — 庫内作業オペレーション",
  description:
    "ピッキング・梱包の標準時間と能率を、段取り時間を切り分けて公平に評価するオペレーション・ダッシュボード。",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafaf9" },
    { media: "(prefers-color-scheme: dark)", color: "#09090b" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="ja"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable} ${notoJP.variable}`}
    >
      <body className="min-h-dvh antialiased">
        <ThemeProvider>
          <div className="field" aria-hidden />
          {/* The shell lives in the layout so loading.tsx and error.tsx render
              inside the chrome instead of replacing the whole screen. */}
          <AppShell>{children}</AppShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
