import { NavLink, Route, Routes } from 'react-router-dom';
import {
  BarChart3,
  BookOpenCheck,
  ClipboardList,
  GraduationCap,
  Layers,
  ListChecks,
  RotateCcw,
  SlidersHorizontal,
} from 'lucide-react';
import { FormEvent, useState } from 'react';
import { DashboardPage } from '../pages/DashboardPage';
import { DailyWorkPage } from '../pages/DailyWorkPage';
import { ErrorJournalPage } from '../pages/ErrorJournalPage';
import { OperatorPage } from '../pages/OperatorPage';
import { ProgramPage } from '../pages/ProgramPage';
import { ReviewQueuePage } from '../pages/ReviewQueuePage';
import { SlicePage } from '../pages/SlicePage';
import { TopicLifecyclePage } from '../pages/TopicLifecyclePage';
import {
  getOperatorMode,
  getStoredApiToken,
  setOperatorMode,
  setStoredApiToken,
} from '../shared/api/client';

const studentNavItems = [
  { to: '/', label: 'Прогресс', icon: BarChart3 },
  { to: '/program', label: 'Программа', icon: GraduationCap },
  { to: '/topics', label: 'Темы', icon: Layers },
  { to: '/daily', label: 'Сегодня', icon: BookOpenCheck },
  { to: '/slice', label: 'Срез', icon: ListChecks },
  { to: '/errors', label: 'Ошибки', icon: ClipboardList },
  { to: '/review', label: 'Повторение', icon: RotateCcw },
];

const operatorNavItem = {
  to: '/operator',
  label: 'Оператор',
  icon: SlidersHorizontal,
};

export function App() {
  const [token, setToken] = useState(getStoredApiToken());
  const [draftToken, setDraftToken] = useState(token);
  const [operatorMode, setOperatorModeState] = useState(getOperatorMode());
  const navItems = operatorMode ? [...studentNavItems, operatorNavItem] : studentNavItems;

  function saveToken(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStoredApiToken(draftToken.trim());
    setToken(draftToken.trim());
  }

  function toggleOperatorMode() {
    const next = !operatorMode;
    setOperatorMode(next);
    setOperatorModeState(next);
  }

  if (!token) {
    return (
      <main className="tokenGate">
        <form className="panel tokenPanel" onSubmit={saveToken}>
          <h1>EGE Mentor</h1>
          <p className="muted">Введите семейный API-токен из `.env`, чтобы открыть LAN-пилот.</p>
          <input
            autoFocus
            onChange={(event) => setDraftToken(event.target.value)}
            placeholder="X-EGE-MENTOR-TOKEN"
            type="password"
            value={draftToken}
          />
          <button type="submit">Открыть</button>
        </form>
      </main>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brandMark">85</span>
          <div>
            <strong>EGE Mentor</strong>
            <span>family pilot</span>
          </div>
        </div>
        <button type="button" className="modeToggle" onClick={toggleOperatorMode}>
          <strong>{operatorMode ? 'Operator mode: on' : 'Operator mode: off'}</strong>
          <span>
            {operatorMode
              ? 'Операторские действия открыты'
              : 'Показать operator surface'}
          </span>
        </button>
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink key={item.to} to={item.to} className="navLink">
                <Icon size={18} />
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/program" element={<ProgramPage />} />
          <Route path="/topics" element={<TopicLifecyclePage />} />
          <Route path="/daily" element={<DailyWorkPage />} />
          <Route path="/slice" element={<SlicePage />} />
          <Route path="/errors" element={<ErrorJournalPage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route path="/operator" element={<OperatorPage />} />
        </Routes>
      </main>
    </div>
  );
}
