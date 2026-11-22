import type { Metadata } from "next";
import AuditLogClient from "./AuditLogClient";

export const metadata: Metadata = { title: "Audit Log" };

export default function AuditLogPage() {
  return <AuditLogClient />;
}
