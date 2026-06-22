import { useQuery } from '@tanstack/react-query';
import { errorMessage, getCurrentStudent, getReviews } from '../shared/api/client';

export function ReviewQueuePage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const reviews = useQuery({
    queryKey: ['reviews', studentId],
    queryFn: () => getReviews(studentId ?? ''),
    enabled: Boolean(studentId),
  });

  return (
    <section>
      <div className="pageHeader">
        <h1>Повторение</h1>
        <p>Карточки +7/+30, чтобы видно какие темы на возврате.</p>
      </div>
      {studentQuery.error || reviews.error ? (
        <div className="state stateError">{errorMessage(studentQuery.error || reviews.error)}</div>
      ) : null}
      {reviews.isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="panel">
        <h2>Карточки</h2>
        {reviews.data?.length ? (
          <div className="tableList">
            {reviews.data.map((item) => (
              <article className="tableRow" key={item.id}>
                <div>
                  <strong>{item.topic_title}</strong>
                  <span>{item.subject} · {new Date(item.due_date).toLocaleDateString('ru-RU')}</span>
                </div>
                <div>
                  <b>{item.status}</b>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Повторений пока нет.</p>
        )}
      </div>
    </section>
  );
}
