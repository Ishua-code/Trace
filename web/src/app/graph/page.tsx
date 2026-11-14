import type { Metadata } from "next";
import { GraphClient } from "./GraphClient";

export const metadata: Metadata = { title: "Failure Propagation Graph" };

export default function GraphPage() {
  return <GraphClient />;
}
