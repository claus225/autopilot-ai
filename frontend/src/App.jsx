import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);

  async function prepareTask(event) {
    event.preventDefault();
    setBusy(true);
    setResult("");
    try {
      const response = await fetch(`${API}/api/tasks/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description }),
      });
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setResult(data.message);
    } catch {
      setResult("API indisponible. Démarre le backend puis réessaie.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="shell">
      <header className="topbar"><span className="mark">A</span><span>AutoPilot AI</span><span className="status">Prototype</span></header>
      <section className="hero">
        <p className="eyebrow">ASSISTANT HYBRIDE • SÉCURITÉ D'ABORD</p>
        <h1>Tu prépares.<br /><span>AutoPilot organise.</span></h1>
        <p className="intro">Décris une tâche : l'assistant prépare une proposition. Rien n'est exécuté automatiquement dans cette version.</p>
      </section>
      <section className="panel">
        <h2>Nouvelle tâche</h2>
        <form onSubmit={prepareTask}>
          <label htmlFor="title">Que veux-tu préparer ?</label>
          <input id="title" value={title} onChange={e => setTitle(e.target.value)} maxLength={120} required placeholder="Ex. Préparer un rappel pour demain" />
          <label htmlFor="description">Détails (facultatif)</label>
          <textarea id="description" value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} rows={3} placeholder="Ajoute quelques précisions…" />
          <button disabled={busy || !title.trim()}>{busy ? "Préparation…" : "Préparer la tâche"}</button>
        </form>
        {result && <p className="result" role="status">{result}</p>}
      </section>
      <footer><span>Contrôle humain activé</span><span>•</span><span>Aucune action externe autorisée</span></footer>
    </main>
  );
}
