import { Inter, Noto_Sans_TC } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const notoSansTC = Noto_Sans_TC({
  subsets: ["latin"],
  weight: ["300", "400", "500", "700"],
  variable: "--font-noto",
  display: "swap",
});

export const metadata = {
  title: "AI Trading Pro - 台股智能交易系統",
  description: "專業的台灣股票當沖交易系統，提供AI驅動的股票推薦、策略回測和風險管理功能。",
};

export default function RootLayout({ children }) {
  return (
    <html lang="zh-TW" className={`${inter.variable} ${notoSansTC.variable} dark`}>
      <body className="font-sans antialiased">
        <div className="relative flex min-h-screen flex-col bg-background">
          {children}
        </div>
      </body>
    </html>
  );
}
