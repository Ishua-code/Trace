"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { PersonaProvider } from "@/lib/persona";
import { MockApiProvider } from "@/components/MockApiProvider";
import { ToastProvider } from "@/components/ToastProvider";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <MockApiProvider>
        <ToastProvider>
          <PersonaProvider>{children}</PersonaProvider>
        </ToastProvider>
      </MockApiProvider>
    </ThemeProvider>
  );
}
