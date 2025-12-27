function App() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#e2e8f0,_#f8fafc_55%,_#ffffff_100%)] text-slate-900">
      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-20 sm:px-10 lg:px-12">
        <header className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700 p-10 text-slate-50 shadow-2xl shadow-slate-900/25">
          <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-200/70">HippoBox</p>
          <h1 className="mt-3 text-4xl font-semibold sm:text-5xl">Personal Knowledge Vault</h1>
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-200/80">
            FastAPI + MCP backend with a lightweight React UI. This is the monolithic frontend that ships with the
            server.
          </p>
        </header>
        <section className="rounded-2xl bg-white p-8 shadow-xl shadow-slate-900/10">
          <h2 className="text-xl font-semibold text-slate-900">Next steps</h2>
          <ul className="mt-4 list-disc space-y-2 pl-5 text-slate-700">
            <li>Run the API on http://localhost:8000</li>
            <li>Build the UI with npm run build</li>
            <li>Serve dist/ from FastAPI at /</li>
          </ul>
        </section>
      </main>
    </div>
  );
}

export default App;