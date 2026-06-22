import { useQuery } from '@tanstack/react-query';
import { errorMessage, getCurrentStudent, getProgram, type TopicState } from '../shared/api/client';

const STATE_LABEL: Record<TopicState, string> = {
  open: 'Не начата',
  in_work: 'В работе',
  under_review: 'На повторении',
  confirmed: 'Подтверждена',
  back_to_work: 'Возврат провален',
};

const STATE_BADGE: Record<TopicState, string> = {
  open: 'badge--open',
  in_work: 'badge--work',
  under_review: 'badge--review',
  confirmed: 'badge--confirmed',
  back_to_work: 'badge--back',
};

export function ProgramPage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const { data, isLoading, error } = useQuery({
    queryKey: ['program', studentId],
    queryFn: () => getProgram(studentId ?? ''),
    enabled: Boolean(studentId),
  });

  return (
    <section>
      <div className="pageHeader">
        <h1>Программа</h1>
        <p>Где ребёнок по плану подготовки: темы по фазам и что уже закрыто. Текущая фаза подсвечена.</p>
      </div>
      {studentQuery.error || error ? (
        <div className="state stateError">{errorMessage(studentQuery.error || error)}</div>
      ) : null}
      {isLoading ? <div className="state">Загрузка...</div> : null}
      {data?.map((phase) => (
        <div className={phase.is_current ? 'panel panel--current' : 'panel'} key={phase.key}>
          <div className="pageHeader" style={{ marginBottom: 8 }}>
            <h2 style={{ margin: 0 }}>
              {phase.label}
              {phase.is_current ? ' · сейчас' : ''}
            </h2>
            <p style={{ margin: 0 }}>
              прогресс {phase.percent}% · закрыто {phase.coverage.confirmed} · в процессе{' '}
              {phase.coverage.in_progress} · не начато {phase.coverage.open} из {phase.coverage.total}
            </p>
            <div className="progressBar" aria-hidden>
              <div className="progressFill" style={{ width: `${phase.percent}%` }} />
            </div>
          </div>
          {phase.topics.length ? (
            <div className="tableList">
              {phase.topics.map((topic) => (
                <article className="tableRow" key={topic.topic_id}>
                  <div>
                    <strong>{topic.topic_title}</strong>
                    <span>{topic.subject === 'math_profile' ? 'Профматематика' : 'Информатика'}</span>
                  </div>
                  <div>
                    <span className={`badge ${STATE_BADGE[topic.state]}`}>{STATE_LABEL[topic.state]}</span>
                    <small>
                      банк: {topic.tasks_in_bank} · решено: {topic.solved_count}
                      {topic.percent !== null ? ` · ${topic.percent}%` : ' · —'}
                      {topic.reviews_due_today > 0 ? ` · повторов: ${topic.reviews_due_today}` : ''}
                      {topic.error_count > 0 ? ` · ошибок: ${topic.error_count}` : ''}
                    </small>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <p className="muted">Впереди — гранулярных тем пока нет.</p>
          )}
        </div>
      ))}
    </section>
  );
}
