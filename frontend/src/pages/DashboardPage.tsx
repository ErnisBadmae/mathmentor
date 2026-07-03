import { useQuery } from '@tanstack/react-query';
import {
  errorMessage,
  getCurrentStudent,
  getDashboard,
  getDiagnostics,
  getScoreEvents,
  type ScoreEvent,
  type Subject,
} from '../shared/api/client';

function subjectLabel(subject: string) {
  return subject === 'math_profile' ? 'Профильная математика' : 'Информатика';
}

function scoreKindLabel(kind: string) {
  const labels: Record<string, string> = {
    baseline: 'Базлайн',
    exam_variant: 'Пробник',
    exam_like_slice: 'Мини-вариант',
    weekly_variant: 'Недельный вариант',
    topic_check: 'Срез темы',
  };
  return labels[kind] ?? kind;
}

function scoreDelta(current: ScoreEvent, previous: ScoreEvent | undefined) {
  if (!previous) return null;
  const delta = current.score - previous.score;
  if (delta === 0) return 'без изменений';
  return `${delta > 0 ? '+' : ''}${delta}`;
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
  const scoreEventsQuery = useQuery({
    queryKey: ['score-events', studentId],
    queryFn: () => getScoreEvents(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const mentorNotes = data?.mentor_notes ?? [];
  const topErrors = data?.top_errors ?? [];
  const diagnostics = diagnosticsQuery.data ?? [];
  const scoreEvents = scoreEventsQuery.data ?? [];
  const retention = data?.retention;
  const scoreEventsBySubject = scoreEvents.reduce<Record<Subject, ScoreEvent[]>>(
    (acc, event) => {
      acc[event.subject].push(event);
      return acc;
    },
    { math_profile: [], informatics: [] },
  );

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
        {retention ? (
          <article className={retention.at_risk ? 'metric metricWarning' : 'metric'}>
            <span>Ритм недели</span>
            <strong>{retention.active_days}/{retention.target_active_days}</strong>
            <small>
              {retention.at_risk
                ? 'Меньше 3 активных дней к среде'
                : `Летний режим: ${retention.daily_task_target} задач/день`}
            </small>
          </article>
        ) : null}
      </div>
      <div className="panel">
        <h2>Тренд баллов</h2>
        {scoreEventsQuery.error ? (
          <p className="muted">{errorMessage(scoreEventsQuery.error)}</p>
        ) : data?.tracks.length ? (
          <div className="tableList">
            {data.tracks.map((track) => {
              const events = scoreEventsBySubject[track.subject];
              const latest = events[0];
              const previous = events[1];
              const delta = latest ? scoreDelta(latest, previous) : null;
              return (
                <article className="tableRow" key={track.subject}>
                  <div>
                    <strong>{subjectLabel(track.subject)}</strong>
                    {latest ? (
                      <span>
                        {scoreKindLabel(latest.kind)} · {new Date(latest.occurred_on).toLocaleDateString('ru-RU')}
                        {latest.note ? ` · ${latest.note}` : ''}
                      </span>
                    ) : (
                      <span>Пробников пока нет.</span>
                    )}
                  </div>
                  <div>
                    <b>{track.current_score}/{track.target_score}</b>
                    <small>{delta ? `Дельта: ${delta}` : `До цели: ${track.score_gap}`}</small>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <p className="muted">Пока нет score events.</p>
        )}
      </div>
      <div className="panel">
        <h2>Обратная связь наставника</h2>
        <div className="tableList">
          {mentorNotes.length ? mentorNotes.map((note) => (
            <article className="tableRow" key={note.id}>
              <div>
                {note.topic_title && <strong>{note.topic_title}</strong>}
                <span style={{ whiteSpace: 'pre-wrap' }}>{note.body}</span>
              </div>
              <div>
                <small>{new Date(note.created_at).toLocaleDateString('ru-RU')}</small>
                <br />
                <small>
                  {note.delivered_at
                    ? `✅ отправлено ученику ${new Date(note.delivered_at).toLocaleDateString('ru-RU')}`
                    : '⏳ ожидает отправки'}
                </small>
              </div>
            </article>
          )) : <p className="muted">Пока нет заметок от наставника.</p>}
        </div>
      </div>
      <div className="panel">
        <h2>Диагностика (срезы)</h2>
        <div className="tableList">
          {diagnosticsQuery.error ? (
            <p className="muted">{errorMessage(diagnosticsQuery.error)}</p>
          ) : diagnostics.length ? diagnostics.map((srez) => (
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
          {topErrors.length ? topErrors.map((item) => (
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
