import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { getCurrentStudent, getTodayMissions, submitAttempt } from '../shared/api/client';

export function DailyWorkPage() {
  const queryClient = useQueryClient();
  const [selectedMission, setSelectedMission] = useState<string | null>(null);
  const [answer, setAnswer] = useState('');
  const [mode, setMode] = useState<'clean_sheet' | 'with_hint'>('clean_sheet');
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const { data: missions, isLoading } = useQuery({
    queryKey: ['today', studentId],
    queryFn: () => getTodayMissions(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const mutation = useMutation({
    mutationFn: submitAttempt,
    onSuccess: () => {
      setAnswer('');
      void queryClient.invalidateQueries({ queryKey: ['today', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['manual-reviews', studentId] });
    },
  });
  const mission = missions?.find((item) => item.id === selectedMission) ?? missions?.[0];

  return (
    <section>
      <div className="pageHeader">
        <h1>Сегодня</h1>
        <p>Выберите миссию, затем решите.</p>
      </div>
      {studentQuery.error ? <div className="state stateError">{studentQuery.error.message}</div> : null}
      {isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="workLayout">
        <div className="panel missionList">
          <h2>Миссии</h2>
          {missions?.length ? missions.map((item) => (
            <button className={item.id === mission?.id ? 'missionButton active' : 'missionButton'} key={item.id} onClick={() => setSelectedMission(item.id)} type="button">
              <strong>{item.title}</strong>
              {item.statement ? <span className="missionPreview">{item.statement}</span> : null}
              <span className="missionMeta">{item.subject} · порог {item.threshold_percent}%</span>
            </button>
          )) : <p className="muted">Активных миссий пока нет.</p>}
        </div>
        <div className="panel attemptPanel">
          <h2>{mission?.title ?? 'Выберите миссию'}</h2>
          {mission?.statement ? (
            <div className="taskStatement">
              <span>Условие</span>
              <p>{mission.statement}</p>
            </div>
          ) : null}
          <p className="muted">{mission?.instructions ?? 'Чтобы увидеть условие, выберите миссию слева.'}</p>
          <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Введите ответ так, как написали бы его на чистовике экзамена" />
          <div className="attemptControls">
            <label><input checked={mode === 'clean_sheet'} onChange={() => setMode('clean_sheet')} type="radio" /> Чистовик</label>
            <label><input checked={mode === 'with_hint'} onChange={() => setMode('with_hint')} type="radio" /> С подсказкой</label>
            <button disabled={!mission || !answer.trim() || mutation.isPending} onClick={() => mission && mutation.mutate({ mission_id: mission.id, kind: mission.subject === 'informatics' ? 'code' : 'text', mode, answer_text: answer, code_text: mission.subject === 'informatics' ? answer : undefined })} type="button">
              Отправить ответ
            </button>
          </div>
          {mutation.error ? <div className="state stateError">{mutation.error.message}</div> : null}
          {mutation.data ? (
            <div className={mutation.data.status === 'needs_manual_review' ? 'resultBox warningBox' : 'resultBox'}>
              <strong>{mutation.data.status === 'needs_manual_review' ? 'Нужна ручная проверка' : `Статус: ${mutation.data.status}`}</strong>
              <p>{mutation.data.feedback}</p>
              <small>{mutation.data.next_action}</small>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
