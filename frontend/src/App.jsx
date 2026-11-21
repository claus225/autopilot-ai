import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const SETTINGS_KEY = "autopilot-reminder-settings";
const SENT_KEY = "autopilot-reminders-sent";

function readSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}");
    return { enabled: saved.enabled === true, time: /^([01]\d|2[0-3]):[0-5]\d$/.test(saved.time) ? saved.time : "08:00" };
  } catch {
    return { enabled: false, time: "08:00" };
  }
}

export default function App() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [tasks, setTasks] = useState([]);
  const [reminders, setReminders] = useState({ items: [], counts: { overdue: 0, today: 0, upcoming: 0 } });
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadingTasks, setLoadingTasks] = useState(true);
  const [notificationSettings, setNotificationSettings] = useState(readSettings);
  const [notificationStatus, setNotificationStatus] = useState("");
  const [nextAction, setNextAction] = useState(null);
  const [assistantStatus, setAssistantStatus] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatBusy, setChatBusy] = useState(false);

  async function loadTasks() {
    try {
      const response = await fetch(`${API}/api/tasks`);
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setTasks(data.items);
      const statusResponse = await fetch(`${API}/api/assistant/status`);
      if (statusResponse.ok) setAssistantStatus(await statusResponse.json());
      const suggestionResponse = await fetch(`${API}/api/assistant/next-action`);
      if (suggestionResponse.ok) setNextAction(await suggestionResponse.json());
      const reminderResponse = await fetch(`${API}/api/reminders?days=7`);
      if (reminderResponse.ok) setReminders(await reminderResponse.json());
    } catch {
      setNotice("Impossible de charger l'historique. Vérifie que l'API est démarrée.");
    } finally {
      setLoadingTasks(false);
    }
  }

  useEffect(() => { loadTasks(); }, []);

  useEffect(() => {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(notificationSettings)); } catch { /* storage may be unavailable */ }
  }, [notificationSettings]);

  useEffect(() => {
    if (!notificationSettings.enabled || !("Notification" in window) || Notification.permission !== "granted") return undefined;

    const checkDueTasks = () => {
      const now = new Date();
      const today = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, "0"), String(now.getDate()).padStart(2, "0")].join("-");
      const currentTime = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
      if (currentTime < notificationSettings.time) return;

      let sent = {};
      try { sent = JSON.parse(localStorage.getItem(SENT_KEY) || "{}"); } catch { sent = {}; }
      tasks.filter(task => task.status === "todo" && task.due_date === today).forEach(task => {
        const key = `${today}:${task.id}`;
        if (sent[key]) return;
        new Notification("AutoPilot AI — échéance aujourd'hui", {
          body: task.title,
          tag: key,
          icon: "/favicon.ico",
        });
        sent[key] = true;
      });
      try { localStorage.setItem(SENT_KEY, JSON.stringify(sent)); } catch { /* notification still shown */ }
    };

    checkDueTasks();
    const intervalId = window.setInterval(checkDueTasks, 30_000);
    return () => window.clearInterval(intervalId);
  }, [notificationSettings, tasks]);

  async function enableNotifications() {
    if (!("Notification" in window)) {
      setNotificationStatus("Ce navigateur ne prend pas en charge les notifications.");
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") {
        setNotificationSettings(current => ({ ...current, enabled: false }));
        setNotificationStatus("Autorisation refusée. Tu peux la modifier dans les paramètres du navigateur.");
        return;
      }
      setNotificationSettings(current => ({ ...current, enabled: true }));
      setNotificationStatus("Notifications activées sur cet appareil lorsque l'application reste ouverte.");
    } catch {
      setNotificationStatus("Impossible d'activer les notifications dans ce navigateur.");
    }
  }

  function disableNotifications() {
    setNotificationSettings(current => ({ ...current, enabled: false }));
    setNotificationStatus("Notifications désactivées.");
  }


  async function sendChat(event) {
    event.preventDefault();
    const content = chatInput.trim();
    if (!content || chatBusy) return;
    const nextMessages = [...chatMessages, { role: "user", content }];
    setChatMessages(nextMessages);
    setChatInput("");
    setChatBusy(true);
    try {
      const response = await fetch(\`\${API}/api/assistant/chat\`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages.slice(-10) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Assistant local indisponible.");
      setChatMessages(current => [...current, { role: "assistant", content: data.reply }]);
    } catch (error) {
      setChatMessages(current => [...current, { role: "assistant", content: error.message || "Impossible de joindre l'assistant local." }]);
    } finally {
      setChatBusy(false);
    }
  }

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
      const suggestionResponse = await fetch(`${API}/api/assistant/next-action`);
      if (suggestionResponse.ok) setNextAction(await suggestionResponse.json());
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
      const suggestionResponse = await fetch(`${API}/api/assistant/next-action`);
      if (suggestionResponse.ok) setNextAction(await suggestionResponse.json());
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
        <span className="status">Prototype v0.5</span>
      </header>

      <section className="hero">
        <p className="eyebrow">ASSISTANT HYBRIDE • SÉCURITÉ D'ABORD</p>
        <h1>Tu prépares.<br /><span>AutoPilot organise.</span></h1>
        <p className="intro">Note tes tâches, ajoute une échéance et reçois un rappel local lorsque l'application est ouverte. Aucun message ni action externe n’est déclenché automatiquement.</p>
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

      <section className="reminder-panel" aria-live="polite">
        <div className="section-heading">
          <h2>Aperçu des rappels</h2>
          <span>7 prochains jours</span>
        </div>
        <div className="reminder-counts">
          <div><strong>{reminders.counts.overdue}</strong><small>En retard</small></div>
          <div><strong>{reminders.counts.today}</strong><small>Aujourd’hui</small></div>
          <div><strong>{reminders.counts.upcoming}</strong><small>À venir</small></div>
        </div>
        {reminders.items.length > 0 ? (
          <ul className="reminder-list">
            {reminders.items.map(item => (
              <li key={item.id}>
                <span>{item.title}</span>
                <small>{item.reminder_type === "overdue" ? "En retard" : item.reminder_type === "today" ? "À faire aujourd’hui" : "Échéance proche"} · {new Date(item.due_date + "T00:00:00").toLocaleDateString("fr-FR")}</small>
              </li>
            ))}
          </ul>
        ) : <p className="empty">Aucune échéance à signaler sur cette période.</p>}
        <p className="reminder-note">L'aperçu ne déclenche aucune notification à lui seul.</p>
      </section>

      <section className="notification-panel">
        <div className="section-heading"><h2>Notifications locales</h2><span>{notificationSettings.enabled ? "Activées" : "Désactivées"}</span></div>
        <label htmlFor="reminder-time">Heure du rappel quotidien</label>
        <input id="reminder-time" type="time" value={notificationSettings.time} onChange={event => setNotificationSettings(current => ({ ...current, time: event.target.value }))} />
        <p className="reminder-note">À cette heure ou après, une notification est affichée pour chaque tâche non terminée dont l'échéance est aujourd'hui. Une seule notification par tâche et par jour.</p>
        {notificationSettings.enabled ? (
          <button className="secondary-button" type="button" onClick={disableNotifications}>Désactiver les notifications</button>
        ) : (
          <button type="button" onClick={enableNotifications}>Autoriser et activer les notifications</button>
        )}
        {notificationStatus && <p className="result" role="status">{notificationStatus}</p>}
        <p className="reminder-note">Limite : les notifications fonctionnent uniquement si le site est ouvert et si le navigateur les autorise. Elles ne sont pas envoyées lorsque l'application est fermée.</p>
      </section>



      <section className="assistant-status-panel" aria-live="polite">
        <strong>{assistantStatus?.connected ? "Moteur IA connecté" : "Moteur IA non connecté"}</strong>
        <p>{assistantStatus?.message || "Vérification de la configuration IA…"}</p>
      </section>


      <section className="chat-panel">
        <div className="section-heading"><h2>Assistant IA local</h2><span>{assistantStatus?.connected ? "Prêt" : "En attente"}</span></div>
        <p className="reminder-note">Les messages sont traités par le modèle installé sur cet ordinateur. Aucun accès aux fichiers, au navigateur ou aux comptes n'est accordé à l'assistant.</p>
        <div className="chat-transcript" aria-live="polite">
          {chatMessages.length === 0 ? <p className="empty">Installe et démarre le modèle local pour commencer une conversation.</p> : chatMessages.map((message, index) => (
            <div className={\`chat-bubble \${message.role}\`} key={index}>
              <strong>{message.role === "user" ? "Toi" : "AutoPilot AI"}</strong>
              <p>{message.content}</p>
            </div>
          ))}
          {chatBusy && <p className="reminder-note">L'assistant prépare sa réponse…</p>}
        </div>
        <form onSubmit={sendChat} className="chat-form">
          <label htmlFor="assistant-message">Ton message</label>
          <textarea id="assistant-message" value={chatInput} onChange={event => setChatInput(event.target.value)} maxLength={2000} rows={3} placeholder="Ex. Aide-moi à organiser ma journée…" />
          <button disabled={chatBusy || !chatInput.trim() || !assistantStatus?.connected}>{chatBusy ? "Réponse en cours…" : "Envoyer au modèle local"}</button>
        </form>
      </section>

      <section className="assistant-panel" aria-live="polite">
        <div className="section-heading"><h2>Assistant de priorité</h2><span>Conseil automatique</span></div>
        {nextAction?.suggestion ? (
          <>
            <p className="assistant-priority">Priorité : {nextAction.priority === "urgent" ? "Urgente" : nextAction.priority === "high" ? "Élevée" : "Normale"}</p>
            <strong>{nextAction.suggestion.title}</strong>
            <p className="reminder-note">{nextAction.reason}</p>
          </>
        ) : <p className="empty">{nextAction?.reason || "Analyse des tâches…"}</p>}
        <p className="reminder-note">Conseil fondé sur des règles simples, pas encore sur un modèle IA. Aucune tâche n'est exécutée.</p>
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
