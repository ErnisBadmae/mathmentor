import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import {
  errorMessage,
  getCurrentStudent,
  getTodayMissions,
  submitAttempt,
  type Mission,
} from '../shared/api/client';

function isPart2Mission(mission: Mission): boolean {
  return mission.ai_policy === 'manual_gate' && mission.source_ref?.startsWith('part2:text:') === true;
}

export function Part2Page() {
  const queryClient = useQueryClient();
  const [selectedMission, setSelectedMission] = useState<string | null>(null);
  const [solution, setSolution] = useState('');
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const missionsQuery = useQuery({
    queryKey: ['today', studentId],
    queryFn: () => getTodayMissions(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const mutation = useMutation({
    mutationFn: submitAttempt,
    onSuccess: () => {
      setSolution('');
      void queryClient.invalidateQueries({ queryKey: ['today', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
      void queryClient.invalidateQueries({ queryKey: ['manual-reviews', studentId] });
    },
  });
  const missions = (missionsQuery.data ?? []).filter(isPart2Mission);
  const mission = missions.find((item) => item.id === selectedMission) ?? missions[0];

  return (
    <section>
      <div className="pageHeader">
        <h1>Часть 2</h1>
        <p>Текст решения отправляется наставнику. Автопроверки и подсказок здесь нет.</p>
      </div>
      {studentQuery.error || missionsQuery.error ? (
        <div className="state stateError">{errorMessage(studentQuery.error || missionsQuery.error)}</div>
      ) : null}
      {missionsQuery.isLoading ? <div className="state">Загрузка...</div> : null}
      <div className="workLayout">
        <div className="panel missionList">
          <h2>№13 / №15</h2>
          {missions.length ? (
            missions.map((item) => (
              <button
                className={item.id === mission?.id ? 'missionButton active' : 'missionButton'}
                key={item.id}
                onClick={() => setSelectedMission(item.id)}
                type="button"
              >
                <strong>{item.title}</strong>
                {item.statement ? <span className="missionPreview">{item.statement}</span> : null}
                <span className="missionMeta">№{item.task_number ?? 'part 2'} · ручная проверка</span>
              </button>
            ))
          ) : (
            <p className="muted">Активных заданий части 2 пока нет.</p>
          )}
        </div>
        <div className="panel attemptPanel">
          <h2>{mission?.title ?? 'Выберите задание'}</h2>
          {mission?.statement ? (
            <div className="taskStatement">
              <span>Условие</span>
              <p>{mission.statement}</p>
            </div>
          ) : null}
          <p className="muted">
            {mission?.instructions ??
              'Решение появится здесь после назначения задания №13 или №15.'}
          </p>
          <textarea
            value={solution}
            onChange={(event) => setSolution(event.target.value)}
            placeholder="Перенесите полный ход решения: преобразования, ограничения, отбор корней или интервалы, итоговый ответ."
          />
          <div className="attemptControls">
            <button
              disabled={!mission || !solution.trim() || mutation.isPending}
              onClick={() =>
                mission &&
                mutation.mutate({
                  mission_id: mission.id,
                  kind: 'text',
                  mode: 'clean_sheet',
                  answer_text: solution,
                })
              }
              type="button"
            >
              Отправить на проверку
            </button>
          </div>
          {mutation.error ? <div className="state stateError">{errorMessage(mutation.error)}</div> : null}
          {mutation.data ? (
            <div className="resultBox warningBox">
              <strong>Решение ожидает ручной проверки</strong>
              <p>{mutation.data.feedback}</p>
              <small>{mutation.data.next_action}</small>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
