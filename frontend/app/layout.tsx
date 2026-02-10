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
        {/* Map Background */}
        <div 
          className="fixed inset-0 z-[-1] bg-cover bg-center bg-no-repeat opacity-40 grayscale-[30%]"
          style={{ backgroundImage: "url('https://media.valorant-api.com/maps/7eaecc1b-4337-bbf6-6ab9-04b8f06b3319/splash.png')" }}
        />
        <div className="fixed inset-0 z-[-1] bg-gradient-to-b from-black/60 via-[var(--valo-darker)]/70 to-black/90" />
        
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
