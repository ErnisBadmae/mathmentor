import { NavLink, Route, Routes } from 'react-router-dom';
import {
  BarChart3,
  BookOpenCheck,
  ClipboardList,
  FileText,
  GraduationCap,
  Layers,
  ListChecks,
  RotateCcw,
  SlidersHorizontal,
} from 'lucide-react';
import { useState } from 'react';
import { DashboardPage } from '../pages/DashboardPage';
import { DailyWorkPage } from '../pages/DailyWorkPage';
import { ErrorJournalPage } from '../pages/ErrorJournalPage';
import { OperatorPage } from '../pages/OperatorPage';
import { Part2Page } from '../pages/Part2Page';
import { ProgramPage } from '../pages/ProgramPage';
import { ReviewQueuePage } from '../pages/ReviewQueuePage';
import { SlicePage } from '../pages/SlicePage';
import { TheoryPage } from '../pages/TheoryPage';
import { TopicLifecyclePage } from '../pages/TopicLifecyclePage';
import { getOperatorMode, setOperatorMode } from '../shared/api/client';

const operatorModeAvailable = import.meta.env.VITE_OPERATOR_MODE_AVAILABLE !== 'false';

const studentNavItems = [
  { to: '/', label: 'Прогресс', icon: BarChart3 },
  { to: '/program', label: 'Программа', icon: GraduationCap },
  { to: '/topics', label: 'Темы', icon: Layers },
  { to: '/daily', label: 'Сегодня', icon: BookOpenCheck },
  { to: '/part2', label: 'Часть 2', icon: FileText },
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
  const [operatorMode, setOperatorModeState] = useState(operatorModeAvailable && getOperatorMode());
  const navItems =
    operatorModeAvailable && operatorMode ? [...studentNavItems, operatorNavItem] : studentNavItems;

  function toggleOperatorMode() {
    if (!operatorModeAvailable) return;
    const next = !operatorMode;
    setOperatorMode(next);
    setOperatorModeState(next);
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
        {operatorModeAvailable ? (
          <button type="button" className="modeToggle" onClick={toggleOperatorMode}>
            <strong>{operatorMode ? 'Operator mode: on' : 'Operator mode: off'}</strong>
            <span>
              {operatorMode
                ? 'Операторские действия открыты'
                : 'Показать operator surface'}
            </span>
          </button>
        ) : null}
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
          <Route path="/part2" element={<Part2Page />} />
          <Route path="/slice" element={<SlicePage />} />
          <Route path="/theory/:topicId" element={<TheoryPage />} />
          <Route path="/errors" element={<ErrorJournalPage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
          <Route
            path="/operator"
            element={operatorModeAvailable ? <OperatorPage /> : <DashboardPage />}
          />
        </Routes>
      </main>
    </div>
  );
}
