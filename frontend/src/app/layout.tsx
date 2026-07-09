import type { Metadata } from "next";
import { Geist, Geist_Mono, Inter } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

import { AuthProvider } from "@/lib/AuthContext";
import { TelemetryProvider } from "@/lib/TelemetryContext";
import GlobalNavbar from "../components/GlobalNavbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "HospitalAI Command Center",
  description: "Next-generation real-time clinical triage orchestrator",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full bg-slate-950 text-slate-100 antialiased dark">
      <body className={`${inter.className} h-full`}>
        <AuthProvider>
          <TelemetryProvider>
            <GlobalNavbar />
            {children}
          </TelemetryProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
