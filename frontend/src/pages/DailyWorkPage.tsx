import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { DEMO_STUDENT_ID, getTodayMissions, submitAttempt } from '../shared/api/client';

export function DailyWorkPage() {
  const queryClient = useQueryClient();
  const [selectedMission, setSelectedMission] = useState<string | null>(null);
  const [answer, setAnswer] = useState('');
  const [mode, setMode] = useState<'clean_sheet' | 'with_hint'>('clean_sheet');
  const { data: missions, isLoading } = useQuery({
    queryKey: ['today', DEMO_STUDENT_ID],
    queryFn: () => getTodayMissions(DEMO_STUDENT_ID),
  });
  const mutation = useMutation({
    mutationFn: submitAttempt,
    onSuccess: () => {
      setAnswer('');
      void queryClient.invalidateQueries({ queryKey: ['today', DEMO_STUDENT_ID] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard', DEMO_STUDENT_ID] });
    },
  });
  const mission = missions?.find((item) => item.id === selectedMission) ?? missions?.[0];

  return (
    <section>
      <div className="pageHeader">
        <h1>Сегодня</h1>
        <p>Выберите миссию, затем решите.</p>
      </div>
      {isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="workLayout">
        <div className="panel missionList">
          <h2>Миссии</h2>
          {missions?.length ? missions.map((item) => (
            <button className={item.id === mission?.id ? 'missionButton active' : 'missionButton'} key={item.id} onClick={() => setSelectedMission(item.id)} type="button">
              <strong>{item.title}</strong>
              <span>{item.subject} · порог {item.threshold_percent}%</span>
            </button>
          )) : <p className="muted">Активных миссий пока нет.</p>}
        </div>
        <div className="panel attemptPanel">
          <h2>{mission?.title ?? 'Выберите миссию'}</h2>
          <p className="muted">{mission?.instructions ?? 'Чтобы увидеть условие, выберите миссию слева.'}</p>
          <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Введите ответ так, как написали бы его на чистовике экзамена" />
          <div className="attemptControls">
            <label><input checked={mode === 'clean_sheet'} onChange={() => setMode('clean_sheet')} type="radio" /> Чистовик</label>
            <label><input checked={mode === 'with_hint'} onChange={() => setMode('with_hint')} type="radio" /> С подсказкой</label>
            <button disabled={!mission || !answer.trim() || mutation.isPending} onClick={() => mission && mutation.mutate({ mission_id: mission.id, kind: mission.subject === 'informatics' ? 'code' : 'text', mode, answer_text: answer, code_text: mission.subject === 'informatics' ? answer : undefined })} type="button">
              Отправить ответ
            </button>
          </div>
          {mutation.data ? <pre className="resultBox">{JSON.stringify(mutation.data, null, 2)}</pre> : null}
        </div>
      </div>
    </section>
  );
}
