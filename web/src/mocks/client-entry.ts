import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";

const worker = setupWorker(...handlers);
let startPromise: Promise<void> | undefined;

export function startWorker() {
  if (!startPromise) {
    startPromise = worker.start({ quiet: true, onUnhandledRequest: "bypass" }).then(() => undefined);
  }
  return startPromise;
}
