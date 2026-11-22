import type { Metadata } from "next";
import { ApprovalsClient } from "./ApprovalsClient";

export const metadata: Metadata = { title: "Approvals" };

export default function ApprovalsPage() {
  return <ApprovalsClient />;
}
