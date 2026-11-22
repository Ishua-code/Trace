import type { Metadata } from "next";
import { GraphClient } from "./GraphClient";

export const metadata: Metadata = { title: "Failure Propagation Graph" };
export const instant = false;

export default function GraphPage() {
  return <GraphClient />;
}
