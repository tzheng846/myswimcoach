"use client";

import { useState } from "react";
import ReportBuilder from "@/components/portal/ReportBuilder";
import ReportSendList from "@/components/portal/ReportSendList";

export default function ReportsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-bold">Report Cards</h1>
      <p className="mt-1 text-sm text-muted">
        Generate shareable progress reports for parents — pick swimmers, a date
        range, and the metrics to highlight.
      </p>

      <div className="mt-6">
        <ReportBuilder onGenerated={() => setRefreshKey((k) => k + 1)} />
      </div>

      <ReportSendList refreshKey={refreshKey} />
    </div>
  );
}
