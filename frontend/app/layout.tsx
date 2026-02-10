import type { Metadata } from "next";
import { Teko, Rajdhani } from "next/font/google";
import "./globals.css";
import ClientLayout from "./ClientLayout";

const teko = Teko({ subsets: ["latin"], weight: ["300", "400", "500", "600", "700"], variable: "--font-teko" });
const rajdhani = Rajdhani({ subsets: ["latin"], weight: ["400", "500", "600", "700"], variable: "--font-rajdhani" });

export const metadata: Metadata = {
  title: "PaperPlane | Automated Job Applications",
  description: "Intelligent automated job application system",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${teko.variable} ${rajdhani.variable} antialiased min-h-screen relative`}>
        {/* Parallax Background System */}
        <div className="parallax-bg">
          {/* Layer 1: Valorant map — moves slowest */}
          <div
            data-parallax
            data-parallax-speed="0.3"
            className="parallax-layer parallax-map"
            style={{ backgroundImage: "url('https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/splash.png')" }}
          />
          {/* Layer 2: Grid pattern — moves at medium speed */}
          <div
            data-parallax
            data-parallax-speed="0.6"
            className="parallax-layer parallax-grid"
          />
          {/* Layer 3: Gradient overlay with ambient glow — does not move */}
          <div className="parallax-layer parallax-overlay" />
        </div>

        {/* Ambient glow spots for energy feel */}
        <div className="ambient-glow" style={{ top: '10%', left: '15%', background: 'rgba(0, 217, 255, 0.08)' }} />
        <div className="ambient-glow" style={{ bottom: '20%', right: '10%', background: 'rgba(255, 70, 85, 0.06)', animationDelay: '4s' }} />

        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
