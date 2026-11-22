import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AppProviders } from "@/components/AppProviders";

export const metadata: Metadata = {
  title: { default: "TRACE — Audit Intelligence", template: "%s | TRACE" },
  description:
    "TRACE digitizes the full product and revalidation audit lifecycle with the Failure Propagation & Closure Assurance Engine.",
  keywords: ["audit", "non-conformance", "quality", "TRACE", "AuditSphere"],
  robots: { index: false, follow: false }, // internal tool
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <AppProviders>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col overflow-hidden">
              <Header />
              <main
                id="main-content"
                className="flex-1 overflow-y-auto bg-grid p-4 sm:p-6"
                role="main"
              >
                {children}
              </main>
            </div>
          </div>
        </AppProviders>
      </body>
    </html>
  );
}
