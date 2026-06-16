import { useQuery } from '@tanstack/react-query';
import { DEMO_STUDENT_ID, getDashboard } from '../shared/api/client';

function subjectLabel(subject: string) {
  return subject === 'math_profile' ? 'Профильная математика' : 'Информатика';
}

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', DEMO_STUDENT_ID],
    queryFn: () => getDashboard(DEMO_STUDENT_ID),
  });

  if (isLoading) return <div className="state">Загрузка...</div>;
  if (error) return <div className="state stateError">API недоступен. Запустите backend или проверьте VITE_STUDENT_ID.</div>;

  return (
    <section>
      <div className="pageHeader">
        <h1>Прогресс к экзамену</h1>
        <p>Источник данных: backend evidence ledger.</p>
      </div>
      <div className="metricGrid">
        {data?.tracks.map((track) => (
          <article className="metric" key={track.subject}>
            <span>{subjectLabel(track.subject)}</span>
            <strong>{track.current_score}/{track.target_score}</strong>
            <small>Осталось набрать: {track.score_gap}</small>
          </article>
        ))}
        <article className="metric">
          <span>Чистый счёт</span>
          <strong>{Math.round((data?.clean_sheet_ratio ?? 0) * 100)}%</strong>
          <small>Доля попыток без подсказок</small>
        </article>
        <article className="metric">
          <span>Повторения</span>
          <strong>{data?.due_reviews ?? 0}</strong>
          <small>Карточек к повторению</small>
        </article>
      </div>
      <div className="panel">
        <h2>Топ ошибок</h2>
        <div className="errorList">
          {data?.top_errors.length ? data.top_errors.map((item) => (
            <div className="errorRow" key={item.category}>
              <span>{item.category}</span>
              <strong>{item.count}</strong>
            </div>
          )) : <p className="muted">Ошибок пока нет в журнале.</p>}
        </div>
      </div>
    </section>
  );
}
