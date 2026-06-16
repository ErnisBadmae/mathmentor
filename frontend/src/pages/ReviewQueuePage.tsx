import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { applyManualDecision, errorMessage, getCurrentStudent, getManualReviews, getReviews, markReviewResult } from '../shared/api/client';

export function ReviewQueuePage() {
  const queryClient = useQueryClient();
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const reviews = useQuery({
    queryKey: ['reviews', studentId],
    queryFn: () => getReviews(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const manual = useQuery({
    queryKey: ['manual-reviews', studentId],
    queryFn: () => getManualReviews(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const reviewMutation = useMutation({
    mutationFn: ({ id, passed }: { id: string; passed: boolean }) => markReviewResult(id, passed),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['reviews', studentId] }),
  });
  const manualMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'passed' | 'failed' }) => applyManualDecision(id, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['manual-reviews', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['reviews', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['today', studentId] });
    },
  });

  return (
    <section>
      <div className="pageHeader">
        <h1>Повторение</h1>
        <p>Карточки +7/+30 и ручная проверка попыток, которые нельзя засчитывать автоматически.</p>
      </div>
      {studentQuery.error || reviews.error || manual.error ? (
        <div className="state stateError">{errorMessage(studentQuery.error || reviews.error || manual.error)}</div>
      ) : null}
      <div className="panel">
        <h2>Ручная проверка</h2>
        {manual.data?.length ? (
          <div className="tableList">
            {manual.data.map((item) => (
              <article className="tableRow" key={item.id}>
                <div>
                  <strong>{item.mission_title}</strong>
                  <span>{item.feedback}</span>
                </div>
                <div className="rowActions">
                  <button disabled={manualMutation.isPending} onClick={() => manualMutation.mutate({ id: item.id, status: 'passed' })} type="button">Зачесть</button>
                  <button disabled={manualMutation.isPending} onClick={() => manualMutation.mutate({ id: item.id, status: 'failed' })} type="button">В повтор</button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Очередь ручной проверки пуста.</p>
        )}
      </div>
      <div className="panel">
        <h2>Интервальное повторение</h2>
        {reviews.data?.length ? (
          <div className="tableList">
            {reviews.data.map((item) => (
              <article className="tableRow" key={item.id}>
                <div>
                  <strong>{item.topic_title}</strong>
                  <span>{item.subject} · {new Date(item.due_date).toLocaleDateString('ru-RU')} · {item.status}</span>
                </div>
                <div className="rowActions">
                  <button disabled={reviewMutation.isPending} onClick={() => reviewMutation.mutate({ id: item.id, passed: true })} type="button">Зачёт</button>
                  <button disabled={reviewMutation.isPending} onClick={() => reviewMutation.mutate({ id: item.id, passed: false })} type="button">В работу</button>
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
