"use client";

import { useEffect, useState, type ReactNode } from "react";

export function MockApiProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const shouldMock = process.env.NEXT_PUBLIC_API_MOCKING === "enabled" || !process.env.NEXT_PUBLIC_API_URL;

  useEffect(() => {
    if (!shouldMock) return;

    import("@/mocks/browser")
      .then(({ worker }) => worker.start({ quiet: true }))
      .then(() => setReady(true))
      .catch((error: unknown) => {
        console.error("Unable to start the local API mock worker", error);
        setReady(true);
      });
  }, [shouldMock]);

  if (!shouldMock) return children;
  if (!ready) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-slate-400" role="status">Starting TRACE demo…</div>;
  }
  return children;
}
