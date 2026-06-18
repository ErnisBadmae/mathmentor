import { useQuery } from '@tanstack/react-query';
import { errorMessage, getCurrentStudent, getDashboard, getDiagnostics } from '../shared/api/client';

function subjectLabel(subject: string) {
  return subject === 'math_profile' ? 'Профильная математика' : 'Информатика';
}

export function DashboardPage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', studentId],
    queryFn: () => getDashboard(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const diagnosticsQuery = useQuery({
    queryKey: ['diagnostics', studentId],
    queryFn: () => getDiagnostics(studentId ?? ''),
    enabled: Boolean(studentId),
  });

  if (studentQuery.isLoading || isLoading) return <div className="state">Загрузка...</div>;
  if (studentQuery.error || error) return <div className="state stateError">{errorMessage(studentQuery.error || error)}</div>;

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
        <h2>Обратная связь наставника</h2>
        <div className="tableList">
          {data?.mentor_notes.length ? data.mentor_notes.map((note) => (
            <article className="tableRow" key={note.id}>
              <div>
                {note.topic_title && <strong>{note.topic_title}</strong>}
                <span style={{ whiteSpace: 'pre-wrap' }}>{note.body}</span>
              </div>
              <div>
                <small>{new Date(note.created_at).toLocaleDateString('ru-RU')}</small>
              </div>
            </article>
          )) : <p className="muted">Пока нет заметок от наставника.</p>}
        </div>
      </div>
      <div className="panel">
        <h2>Диагностика (срезы)</h2>
        <div className="tableList">
          {diagnosticsQuery.data?.length ? diagnosticsQuery.data.map((srez) => (
            <article className="tableRow" key={`${srez.label}-${srez.occurred_on}`}>
              <div>
                <strong>{srez.label}</strong>
                <span>{subjectLabel(srez.subject)} · {new Date(srez.occurred_on).toLocaleDateString('ru-RU')}</span>
              </div>
              <div>
                <b>{srez.tasks_correct}/{srez.tasks_total}</b>
                <small>{Math.round(srez.percent * 100)}%</small>
              </div>
            </article>
          )) : <p className="muted">Срезов пока нет.</p>}
        </div>
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
