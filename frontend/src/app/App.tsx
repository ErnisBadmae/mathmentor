import { NavLink, Route, Routes } from 'react-router-dom';
import { BarChart3, BookOpenCheck, ClipboardList, RotateCcw } from 'lucide-react';
import { DashboardPage } from '../pages/DashboardPage';
import { DailyWorkPage } from '../pages/DailyWorkPage';
import { ErrorJournalPage } from '../pages/ErrorJournalPage';
import { ReviewQueuePage } from '../pages/ReviewQueuePage';

const navItems = [
  { to: '/', label: '???????', icon: BarChart3 },
  { to: '/daily', label: '???????', icon: BookOpenCheck },
  { to: '/errors', label: '??????', icon: ClipboardList },
  { to: '/review', label: '??????????', icon: RotateCcw },
];

export function App() {
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
          <Route path="/daily" element={<DailyWorkPage />} />
          <Route path="/errors" element={<ErrorJournalPage />} />
          <Route path="/review" element={<ReviewQueuePage />} />
        </Routes>
      </main>
    </div>
  );
}
