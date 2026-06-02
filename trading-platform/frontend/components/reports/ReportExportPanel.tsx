import { fetchReportCsvExport, fetchReportJsonExport } from "@/lib/clientReportsApi";

export function ReportExportPanel() {
  async function exportJson() {
    const payload = await fetchReportJsonExport();
    console.info("Client report JSON export", payload);
  }

  async function exportCsv() {
    const csv = await fetchReportCsvExport();
    console.info("Client report CSV export", csv);
  }

  function printReport() {
    window.print();
  }

  return (
    <section className="rounded-2xl border border-white/10 bg-slate-950/40 p-4">
      <p className="text-[0.68rem] font-bold uppercase tracking-[0.2em] text-slate-500">Export Panel</p>
      <h3 className="mt-1 text-xl font-black text-white">Download & Print</h3>
      <div className="mt-4 grid gap-2 sm:grid-cols-3">
        {[
          ["Export JSON", exportJson],
          ["Export CSV", exportCsv],
          ["Print Report", printReport],
        ].map(([label, handler]) => (
          <button
            className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-4 py-3 text-sm font-black uppercase tracking-[0.12em] text-cyan-100 hover:bg-cyan-300/[0.16]"
            key={String(label)}
            onClick={handler as () => void}
            type="button"
          >
            {String(label)}
          </button>
        ))}
      </div>
      <p className="mt-3 text-xs leading-5 text-slate-400">
        Exports use recorded demo analytics only. CSV returns headers when no reportable data exists.
      </p>
    </section>
  );
}
