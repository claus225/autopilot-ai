import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [tasks, setTasks] = useState([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingTasks, setLoadingTasks] = useState(true);

  async function loadTasks() {
    try {
      const response = await fetch(`${API}/api/tasks`);
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setTasks(data.items);
    } catch {
      setNotice("Impossible de charger l'historique. Vérifie que l'API est démarrée.");
    } finally {
      setLoadingTasks(false);
    }
  }

  useEffect(() => {
    loadTasks();
  }, []);

  async function saveTask(event) {
    event.preventDefault();
    setBusy(true);
    setNotice("");
    try {
      const response = await fetch(`${API}/api/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description, due_date: dueDate || null }),
      });
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setTasks(current => [data.item, ...current]);
      setTitle("");
      setDescription("");
      setDueDate("");
      setNotice(data.message);
    } catch {
      setNotice("API indisponible. Démarre le backend puis réessaie.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleTask(task) {
    const nextStatus = task.status === "completed" ? "todo" : "completed";
    try {
      const response = await fetch(`${API}/api/tasks/${task.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: nextStatus }),
      });
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setTasks(current => current.map(item => item.id === task.id ? data.item : item));
      setNotice(data.message);
    } catch {
      setNotice("Impossible de modifier cette tâche pour le moment.");
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <span className="mark">A</span>
        <span>AutoPilot AI</span>
        <span className="status">Prototype v0.3</span>
      </header>

      <section className="hero">
        <p className="eyebrow">ASSISTANT HYBRIDE • SÉCURITÉ D'ABORD</p>
        <h1>Tu prépares.<br /><span>AutoPilot organise.</span></h1>
        <p className="intro">Note tes tâches, ajoute une échéance et suis leur avancement. L'application n'exécute aucune action sur ton ordinateur ou sur des sites externes.</p>
      </section>

      <section className="panel">
        <h2>Ajouter une tâche</h2>
        <form onSubmit={saveTask}>
          <label htmlFor="title">Que veux-tu faire ?</label>
          <input id="title" value={title} onChange={e => setTitle(e.target.value)} maxLength={120} required placeholder="Ex. Préparer mon planning de demain" />
          <label htmlFor="description">Détails (facultatif)</label>
          <textarea id="description" value={description} onChange={e => setDescription(e.target.value)} maxLength={1000} rows={3} placeholder="Ajoute quelques précisions…" />
          <label htmlFor="due-date">Date limite (facultatif)</label>
          <input id="due-date" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
          <button disabled={busy || !title.trim()}>{busy ? "Enregistrement…" : "Enregistrer la tâche"}</button>
        </form>
        {notice && <p className="result" role="status">{notice}</p>}
      </section>

      <section className="tasks">
        <div className="section-heading">
          <h2>Mon espace de tâches</h2>
          <span>{tasks.length} enregistrée(s)</span>
        </div>
        {loadingTasks ? <p className="empty">Chargement…</p> : tasks.length === 0 ? (
          <p className="empty">Aucune tâche pour le moment. Ajoute ta première tâche ci-dessus.</p>
        ) : (
          <ul className="task-list">
            {tasks.map(task => (
              <li className="task-item" key={task.id}>
                <button className={`check ${task.status === "completed" ? "checked" : ""}`} onClick={() => toggleTask(task)} aria-label={task.status === "completed" ? "Remettre en cours" : "Marquer comme terminée"}>{task.status === "completed" ? "✓" : ""}</button>
                <div className="task-copy">
                  <strong className={task.status === "completed" ? "done" : ""}>{task.title}</strong>
                  {task.description && <p>{task.description}</p>}
                  {task.due_date && <small className="due-date">Échéance : {new Date(`${task.due_date}T00:00:00`).toLocaleDateString("fr-FR")}</small>}
                  <small>{task.status === "completed" ? "Terminée" : "À faire"} · {new Date(task.created_at).toLocaleString("fr-FR")}</small>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <footer><span>Contrôle humain activé</span><span>•</span><span>Aucune action externe autorisée</span></footer>
    </main>
  );
}
