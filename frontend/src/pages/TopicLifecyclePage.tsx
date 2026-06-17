import { useQuery } from '@tanstack/react-query';
import {
  errorMessage,
  getCurrentStudent,
  getTopicLifecycle,
  type TopicLifecycle,
  type TopicState,
} from '../shared/api/client';

const STATE_LABEL: Record<TopicState, string> = {
  open: 'Не начата',
  in_work: 'В работе',
  under_review: 'На повторении',
  confirmed: 'Подтверждена',
  back_to_work: 'Возврат провален',
};

// Weak topics first: failed returns, then active work, then untouched; strong last.
const STATE_ORDER: Record<TopicState, number> = {
  back_to_work: 0,
  in_work: 1,
  open: 2,
  under_review: 3,
  confirmed: 4,
};

function isWeak(topic: TopicLifecycle): boolean {
  return topic.state !== 'confirmed' && topic.state !== 'under_review';
}

export function TopicLifecyclePage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const { data, isLoading, error } = useQuery({
    queryKey: ['topic-lifecycle', studentId],
    queryFn: () => getTopicLifecycle(studentId ?? ''),
    enabled: Boolean(studentId),
  });

  const topics = [...(data ?? [])].sort(
    (a, b) => STATE_ORDER[a.state] - STATE_ORDER[b.state] || a.topic_title.localeCompare(b.topic_title, 'ru'),
  );

  return (
    <section>
      <div className="pageHeader">
        <h1>Темы</h1>
        <p>Состояние каждой темы вычисляется из миссий, evidence и повторов. Слабые — сверху.</p>
      </div>
      {studentQuery.error || error ? (
        <div className="state stateError">{errorMessage(studentQuery.error || error)}</div>
      ) : null}
      {isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="panel">
        {topics.length ? (
          <div className="tableList">
            {topics.map((topic) => (
              <article className="tableRow" key={topic.topic_id}>
                <div>
                  <strong>{topic.topic_title}</strong>
                  <span>
                    {topic.subject === 'math_profile' ? 'Профматематика' : 'Информатика'}
                    {topic.top_error_category ? ` · частая ошибка: ${topic.top_error_category}` : ''}
                  </span>
                </div>
                <div>
                  <b style={{ color: isWeak(topic) ? '#c0392b' : '#27ae60' }}>{STATE_LABEL[topic.state]}</b>
                  <small>
                    банк: {topic.tasks_in_bank} · решено: {topic.solved_count}
                    {topic.reviews_due_today > 0 ? ` · повторов: ${topic.reviews_due_today}` : ''}
                    {topic.error_count > 0 ? ` · ошибок: ${topic.error_count}` : ''}
                  </small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Пока нет тем с активностью.</p>
        )}
      </div>
    </section>
  );
}
