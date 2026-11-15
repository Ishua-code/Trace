"use client";

import { type ReactNode } from "react";
import { useEffect } from "react";

declare global {
  interface Window {
    TraceMsw?: { startWorker: () => Promise<void> };
  }
}

export function MockApiProvider({ children }: { children: ReactNode }) {
  const shouldMock = process.env.NEXT_PUBLIC_API_MOCKING === "enabled" || !process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    if (!shouldMock) return;
    const start = async () => {
      try {
        if (!window.TraceMsw) throw new Error("Mock worker bundle did not initialize");
        await window.TraceMsw.startWorker();
      } catch (error) {
        console.warn("Local API mocks could not start; the frontend will remain available.", error);
      }
    };

    let script: HTMLScriptElement;
    if (window.TraceMsw) {
      start();
    } else {
      script = document.querySelector<HTMLScriptElement>('script[data-trace-msw="true"]') ?? document.createElement("script");
      script.dataset.traceMsw = "true";
      script.src = "/msw-client.js";
      script.async = true;
      script.addEventListener("load", start);
      script.addEventListener("error", () => {
        console.warn("Local API mock bundle did not load; the frontend will remain available.");
      }, { once: true });
      if (!script.isConnected) document.head.appendChild(script);
    }

    return () => {
      script?.removeEventListener("load", start);
    };
  }, [shouldMock]);

  return children;
}
