import { useQuery } from '@tanstack/react-query';
import { getDashboard } from '../shared/api/client';

const DEMO_STUDENT_ID = import.meta.env.VITE_STUDENT_ID ?? '00000000-0000-0000-0000-000000000000';

function subjectLabel(subject: string) {
  return subject === 'math_profile' ? '??????????????' : '???????????';
}

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard', DEMO_STUDENT_ID],
    queryFn: () => getDashboard(DEMO_STUDENT_ID),
  });

  if (isLoading) return <div className="state">????????...</div>;
  if (error) return <div className="state stateError">API ??????????. ????????? backend ??? ????????? VITE_STUDENT_ID.</div>;

  return (
    <section>
      <div className="pageHeader">
        <h1>??????? ??????????</h1>
        <p>???????? ??????: backend evidence ledger.</p>
      </div>
      <div className="metricGrid">
        {data?.tracks.map((track) => (
          <article className="metric" key={track.subject}>
            <span>{subjectLabel(track.subject)}</span>
            <strong>{track.current_score}/{track.target_score}</strong>
            <small>???????? ???????: {track.score_gap}</small>
          </article>
        ))}
        <article className="metric">
          <span>?????? ????</span>
          <strong>{Math.round((data?.clean_sheet_ratio ?? 0) * 100)}%</strong>
          <small>??? ??? ?? ? ?????????</small>
        </article>
        <article className="metric">
          <span>??????????</span>
          <strong>{data?.due_reviews ?? 0}</strong>
          <small>???? ? ????????</small>
        </article>
      </div>
      <div className="panel">
        <h2>??? ??????</h2>
        <div className="errorList">
          {data?.top_errors.length ? data.top_errors.map((item) => (
            <div className="errorRow" key={item.category}>
              <span>{item.category}</span>
              <strong>{item.count}</strong>
            </div>
          )) : <p className="muted">?????? ???? ??? ? ???????.</p>}
        </div>
      </div>
    </section>
  );
}
