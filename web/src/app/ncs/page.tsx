import type { Metadata } from "next";
import { NCsClient } from "./NCsClient";

export const metadata: Metadata = { title: "Non-Conformances" };

export default function NCsPage() {
  return <NCsClient />;
}
