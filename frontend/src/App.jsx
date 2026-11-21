import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

function readCookie(name) {
  const entry = document.cookie.split("; ").find(item => item.startsWith(`${name}=`));
  return entry ? decodeURIComponent(entry.slice(name.length + 1)) : "";
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const method = (options.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrf = readCookie("autopilot_csrf");
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }
  return fetch(`${API}${path}`, { ...options, headers, credentials: "include" });
}
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
  const [securityStatus, setSecurityStatus] = useState(null);
  const [telegramStatus, setTelegramStatus] = useState(null);
  const [securityBusy, setSecurityBusy] = useState(false);
  const [installPrompt, setInstallPrompt] = useState(null);
  const [isInstalled, setIsInstalled] = useState(false);
  const [authMode, setAuthMode] = useState("checking");
  const [authPassword, setAuthPassword] = useState("");
  const [setupToken, setSetupToken] = useState("");
  const [authBusy, setAuthBusy] = useState(false);

  async function loadTasks() {
    try {
      const response = await apiFetch(`/api/tasks`);
      if (!response.ok) throw new Error("API error");
      const data = await response.json();
      setTasks(data.items);
      const telegramResponse = await fetch(`${API}/api/telegram/status`);
      if (telegramResponse.ok) setTelegramStatus(await telegramResponse.json());
      const securityResponse = await fetch(`${API}/api/security/status`);
      if (securityResponse.ok) setSecurityStatus(await securityResponse.json());
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

  useEffect(() => {
    let cancelled = false;
    async function initializeAuth() {
      try {
        const response = await apiFetch("/api/auth/status");
        if (!response.ok) throw new Error("Statut d'authentification indisponible.");
        const status = await response.json();
        let nextMode = "open";
        if (status.owner_configured) {
          const session = await apiFetch("/api/auth/me");
          nextMode = session.ok ? "ready" : "login";
        } else if (status.setup_available) {
          nextMode = "setup";
        }
        if (cancelled) return;
        setAuthMode(nextMode);
        if (nextMode === "ready" || nextMode === "open") await loadTasks();
      } catch {
        if (!cancelled) {
          setAuthMode("offline");
          setNotice("Impossible de joindre l'API AutoPilot AI.");
          setLoadingTasks(false);
        }
      }
    }
    initializeAuth();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    const standalone = window.matchMedia?.("(display-mode: standalone)").matches
      || window.navigator.standalone === true;
    setIsInstalled(standalone);

    const handleInstallPrompt = event => {
      event.preventDefault();
      setInstallPrompt(event);
    };
    const handleInstalled = () => {
      setIsInstalled(true);
      setInstallPrompt(null);
    };

    window.addEventListener("beforeinstallprompt", handleInstallPrompt);
    window.addEventListener("appinstalled", handleInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleInstallPrompt);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  async function installApp() {
    if (!installPrompt) return;
    await installPrompt.prompt();
    await installPrompt.userChoice;
    setInstallPrompt(null);
  }

  useEffect(() => {
    try { localStorage.setItem(SETTINGS_KEY, JSON.stringify(notificationSettings)); } catch { /* storage may be unavailable */ }
  }, [notificationSettings]);

  useEffect(() => {
    if (securityStatus?.emergency_stop_enabled || !notificationSettings.enabled || !("Notification" in window) || Notification.permission !== "granted") return undefined;

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
  }, [notificationSettings, tasks, securityStatus]);

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
    if (!content || chatBusy || securityStatus?.emergency_stop_enabled) return;
    const nextMessages = [...chatMessages, { role: "user", content }];
    setChatMessages(nextMessages);
    setChatInput("");
    setChatBusy(true);
    try {
      const response = await fetch(`${API}/api/assistant/chat`, {
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

  async function toggleEmergencyStop() {
    if (securityBusy) return;
    setSecurityBusy(true);
    try {
      const response = await fetch(`${API}/api/security/emergency-stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: !securityStatus?.emergency_stop_enabled }),
      });
      if (!response.ok) throw new Error("Impossible de modifier l'arrêt d'urgence.");
      const data = await response.json();
      setSecurityStatus(data);
      setNotice(data.message);
      if (data.emergency_stop_enabled) {
        setNotificationSettings(current => ({ ...current, enabled: false }));
      }
    } catch (error) {
      setNotice(error.message || "Le centre de sécurité est indisponible.");
    } finally {
      setSecurityBusy(false);
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


  async function submitAuth(event) {
    event.preventDefault();
    if (authBusy) return;
    setAuthBusy(true);
    setNotice("");
    const isSetup = authMode === "setup";
    try {
      const response = await apiFetch(isSetup ? "/api/auth/setup" : "/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(isSetup ? { setup_token: setupToken, password: authPassword } : { password: authPassword }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Authentification refusée.");
      setAuthPassword("");
      setSetupToken("");
      setAuthMode("ready");
      await loadTasks();
    } catch (error) {
      setNotice(error.message || "Impossible de se connecter.");
    } finally {
      setAuthBusy(false);
    }
  }

  async function logout() {
    try {
      const response = await apiFetch("/api/auth/logout", { method: "POST" });
      if (!response.ok) throw new Error("Impossible de fermer la session.");
      setAuthMode("login");
      setTasks([]);
      setChatMessages([]);
      setNotice("Session fermée.");
    } catch (error) {
      setNotice(error.message || "Erreur pendant la déconnexion.");
    }
  }

  if (authMode === "checking") {
    return <main className="shell"><header className="topbar"><span className="mark">A</span><span>AutoPilot AI</span></header><p className="empty">Vérification de la session sécurisée…</p></main>;
  }

  if (authMode === "login" || authMode === "setup") {
    const isSetup = authMode === "setup";
    return (
      <main className="shell">
        <header className="topbar"><span className="mark">A</span><span>AutoPilot AI</span><span className="status">Espace privé</span></header>
        <section className="hero"><p className="eyebrow">ACCÈS PROPRIÉTAIRE</p><h1>{isSetup ? "Créer ton compte." : "Bon retour."}<br /><span>AutoPilot AI</span></h1><p className="intro">Cet espace est privé. Les identifiants sont envoyés uniquement à ton serveur et ne sont pas enregistrés dans le navigateur.</p></section>
        <section className="panel">
          <h2>{isSetup ? "Configuration initiale" : "Connexion"}</h2>
          <form onSubmit={submitAuth}>
            {isSetup && <><label htmlFor="setup-token">Secret d'initialisation du serveur</label><input id="setup-token" type="password" value={setupToken} onChange={event => setSetupToken(event.target.value)} minLength={32} maxLength={512} autoComplete="off" required /></>}
            <label htmlFor="owner-password">Mot de passe propriétaire</label>
            <input id="owner-password" type="password" value={authPassword} onChange={event => setAuthPassword(event.target.value)} minLength={12} maxLength={1024} autoComplete={isSetup ? "new-password" : "current-password"} required />
            <button disabled={authBusy || authPassword.length < 12 || (isSetup && setupToken.length < 32)}>{authBusy ? "Vérification…" : isSetup ? "Créer le compte privé" : "Se connecter"}</button>
          </form>
          {notice && <p className="result" role="status">{notice}</p>}
          <p className="reminder-note">Ne partage jamais le secret d'initialisation ni ton mot de passe. Après la première création, le compte ne peut plus être recréé depuis cette page.</p>
        </section>
      </main>
    );
  }

  if (authMode === "offline") {
    return <main className="shell"><header className="topbar"><span className="mark">A</span><span>AutoPilot AI</span></header><p className="result">{notice}</p></main>;
  }

  return (
    <main className="shell">
      <header className="topbar">
        <span className="mark">A</span>
        <span>AutoPilot AI</span>
        {authMode === "ready" && <button className="install-button" type="button" onClick={logout}>Déconnexion</button>}
        {isInstalled ? (
          <span className="status">Application installée</span>
        ) : installPrompt ? (
          <button className="install-button" type="button" onClick={installApp}>Installer</button>
        ) : (
          <span className="status">Prototype v0.5</span>
        )}
      </header>
      {!isInstalled && !installPrompt && (
        <p className="install-hint">Après publication HTTPS : sur Android, ouvre le menu Chrome ⋮ puis « Installer l'application » ou « Ajouter à l'écran d'accueil ». Sur iPhone, utilise Partager puis « Sur l'écran d'accueil » si l'option est disponible.</p>
      )}

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



      <section className="security-panel" aria-live="polite">
        <div className="section-heading">
          <h2>Centre de sécurité</h2>
          <span>{securityStatus?.emergency_stop_enabled ? "Pause active" : "Protection active"}</span>
        </div>
        <p className="reminder-note">{securityStatus?.message || "Lecture de l'état de sécurité…"}</p>
        <ul className="security-list">
          <li><span>Actions externes</span><strong>Désactivées</strong></li>
          <li><span>Automatisation du navigateur</span><strong>Désactivée</strong></li>
          <li><span>Agent de contrôle du PC</span><strong>Désactivé</strong></li>
          <li><span>Chat IA</span><strong>{securityStatus?.chat_available ? "Disponible si Ollama est prêt" : "Suspendu"}</strong></li>
          {(securityStatus?.permissions || []).map(permission => (
            <li key={permission.permission_key}>
              <span>{permission.label}</span>
              <strong>{permission.enabled ? "Autorisée" : "Bloquée par défaut"}</strong>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className={securityStatus?.emergency_stop_enabled ? "secondary-button" : "danger-button"}
          onClick={toggleEmergencyStop}
          disabled={securityBusy || !securityStatus}
        >
          {securityBusy ? "Mise à jour…" : securityStatus?.emergency_stop_enabled ? "Désactiver l'arrêt d'urgence" : "Activer l'arrêt d'urgence"}
        </button>
        <p className="reminder-note">L'arrêt d'urgence suspend le chat IA côté serveur et les notifications locales dans cette interface. Les notes et tâches déjà enregistrées restent intactes. Le réglage est enregistré dans SQLite et reste actif après un redémarrage de l'API.</p>
      </section>


      <section className="panel telegram-panel" aria-live="polite">
        <div className="section-heading"><h2>Connexion Telegram</h2><span>{telegramStatus?.connected ? "Connecté" : "À configurer"}</span></div>
        <p className="reminder-note">Bot indiqué : <strong>@Tchek_bot</strong>. Cette identité est celle que tu as communiquée ; elle n'est pas encore vérifiée par Telegram.</p>
        <p>{telegramStatus?.message || "Vérification de la configuration Telegram…"}</p>
        {telegramStatus?.bot?.username && <p className="reminder-note">Bot vérifié : @{telegramStatus.bot.username}</p>}
        <ul className="security-list">
          <li><span>Vérification du bot</span><strong>{telegramStatus?.connected ? "Réussie" : "En attente"}</strong></li>
          <li><span>Publication dans les canaux</span><strong>Désactivée</strong></li>
          <li><span>Envoi d'images et vidéos</span><strong>Désactivé</strong></li>
          <li><span>Création de liens</span><strong>Désactivée</strong></li>
        </ul>
        <p className="reminder-note">Pour connecter le bot, le propriétaire du serveur doit ajouter TELEGRAM_BOT_TOKEN dans les variables secrètes du backend. Ne colle jamais ce token dans cette page, dans GitHub ou dans une conversation. Les fonctions de publication seront ajoutées après vérification et avec confirmation humaine.</p>
      </section>

      <section className="assistant-status-panel" aria-live="polite">
        <strong>{assistantStatus?.connected ? "Moteur IA connecté" : "Moteur IA non connecté"}</strong>
        <p>{assistantStatus?.message || "Vérification de la configuration IA…"}</p>
      </section>


      <section className="chat-panel">
        <div className="section-heading"><h2>Assistant IA local</h2><span>{securityStatus?.emergency_stop_enabled ? "Suspendu par la sécurité" : assistantStatus?.connected ? "Prêt" : "En attente"}</span></div>
        <p className="reminder-note">Les messages sont traités par le modèle installé sur cet ordinateur. Aucun accès aux fichiers, au navigateur ou aux comptes n'est accordé à l'assistant.</p>
        <div className="chat-transcript" aria-live="polite">
          {chatMessages.length === 0 ? <p className="empty">Installe et démarre le modèle local pour commencer une conversation.</p> : chatMessages.map((message, index) => (
            <div className={`chat-bubble ${message.role}`} key={index}>
              <strong>{message.role === "user" ? "Toi" : "AutoPilot AI"}</strong>
              <p>{message.content}</p>
            </div>
          ))}
          {chatBusy && <p className="reminder-note">L'assistant prépare sa réponse…</p>}
        </div>
        <form onSubmit={sendChat} className="chat-form">
          <label htmlFor="assistant-message">Ton message</label>
          <textarea id="assistant-message" value={chatInput} onChange={event => setChatInput(event.target.value)} maxLength={2000} rows={3} placeholder="Ex. Aide-moi à organiser ma journée…" />
          <button disabled={chatBusy || !chatInput.trim() || !assistantStatus?.connected || securityStatus?.emergency_stop_enabled}>{chatBusy ? "Réponse en cours…" : "Envoyer au modèle local"}</button>
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
