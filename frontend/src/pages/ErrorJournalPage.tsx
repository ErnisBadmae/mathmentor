import { useQuery } from '@tanstack/react-query';
import { errorMessage, getCurrentStudent, getErrors } from '../shared/api/client';

export function ErrorJournalPage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const { data, isLoading, error } = useQuery({
    queryKey: ['errors', studentId],
    queryFn: () => getErrors(studentId ?? ''),
    enabled: Boolean(studentId),
  });

  return (
    <section>
      <div className="pageHeader">
        <h1>Журнал ошибок</h1>
        <p>Каждый промах сохраняется как evidence event, чтобы следующий план бил в слабое место.</p>
      </div>
      {studentQuery.error || error ? <div className="state stateError">{errorMessage(studentQuery.error || error)}</div> : null}
      {isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="panel">
        {data?.length ? (
          <div className="tableList">
            {data.map((item) => (
              <article className="tableRow" key={item.id}>
                <div>
                  <strong>{item.topic_title ?? item.subject}</strong>
                  <span>{item.detail}</span>
                </div>
                <div>
                  <b>{item.category}</b>
                  <small>{new Date(item.created_at).toLocaleDateString('ru-RU')}</small>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Ошибок пока нет.</p>
        )}
      </div>
    </section>
  );
}
