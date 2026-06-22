import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FormEvent, useMemo, useState } from 'react';
import {
  applyManualDecision,
  createMission,
  errorMessage,
  getCurrentStudent,
  getManualReviews,
  getReviews,
  getTodayMissions,
  markReviewResult,
  publishMentorNote,
  recordScoreEvent,
  updateMission,
  type Mission,
  type MissionDraft,
} from '../shared/api/client';

type CountDraft = { tasks_total: string; tasks_correct: string };

const EMPTY_COUNTS: CountDraft = { tasks_total: '', tasks_correct: '' };

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

// Counts are sent only when BOTH fields are filled; one-of-two is treated as "no counts"
// so a half-filled row can't silently score as 0 correct (backend also rejects the XOR).
function parseCounts(draft: CountDraft): { tasks_total?: number; tasks_correct?: number } {
  if (!draft.tasks_total.trim() || !draft.tasks_correct.trim()) {
    return {};
  }
  return {
    tasks_total: Number(draft.tasks_total),
    tasks_correct: Number(draft.tasks_correct),
  };
}

function countsPartiallyFilled(draft: CountDraft): boolean {
  return Boolean(draft.tasks_total.trim()) !== Boolean(draft.tasks_correct.trim());
}

function missionToDraft(mission: Mission): MissionDraft {
  return {
    subject: mission.subject,
    title: mission.title,
    instructions: mission.instructions,
    threshold_percent: mission.threshold_percent,
    due_date: mission.due_date,
    timebox_minutes: mission.timebox_minutes,
    topic_id: null,
    task_id: null,
  };
}

export function OperatorPage() {
  const queryClient = useQueryClient();
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;
  const missionsQuery = useQuery({
    queryKey: ['today', studentId],
    queryFn: () => getTodayMissions(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const manualQuery = useQuery({
    queryKey: ['manual-reviews', studentId],
    queryFn: () => getManualReviews(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const reviewsQuery = useQuery({
    queryKey: ['reviews', studentId],
    queryFn: () => getReviews(studentId ?? ''),
    enabled: Boolean(studentId),
  });
  const [createDraft, setCreateDraft] = useState<MissionDraft>({
    subject: 'math_profile',
    title: '',
    instructions: '',
    threshold_percent: 80,
    due_date: '',
    topic_id: '',
    task_id: '',
  });
  const missions = missionsQuery.data ?? [];
  const [selectedMissionId, setSelectedMissionId] = useState<string | null>(null);
  const selectedMission =
    missions.find((mission) => mission.id === selectedMissionId) ?? missions[0] ?? null;
  const [editDraft, setEditDraft] = useState<MissionDraft | null>(null);
  const [scoreDraft, setScoreDraft] = useState({
    subject: 'math_profile',
    score: '80',
    kind: 'exam_variant',
    occurred_on: '',
    note: '',
  });
  const [noteDraft, setNoteDraft] = useState({ body: '', topic_id: '' });
  const [manualCounts, setManualCounts] = useState<Record<string, CountDraft>>({});

  const selectedMissionDraft = useMemo(() => {
    if (!selectedMission) return null;
    if (editDraft && selectedMission.id === selectedMissionId) return editDraft;
    return missionToDraft(selectedMission);
  }, [editDraft, selectedMission, selectedMissionId]);

  const invalidateOperatorData = () => {
    void queryClient.invalidateQueries({ queryKey: ['today', studentId] });
    void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
    void queryClient.invalidateQueries({ queryKey: ['manual-reviews', studentId] });
    void queryClient.invalidateQueries({ queryKey: ['reviews', studentId] });
  };

  const createMissionMutation = useMutation({
    mutationFn: (payload: MissionDraft) => createMission(studentId ?? '', payload),
    onSuccess: () => {
      setCreateDraft({
        subject: createDraft.subject,
        title: '',
        instructions: '',
        threshold_percent: 80,
        due_date: '',
        topic_id: '',
        task_id: '',
      });
      invalidateOperatorData();
    },
  });
  const updateMissionMutation = useMutation({
    mutationFn: ({ missionId, payload }: { missionId: string; payload: Partial<MissionDraft> }) =>
      updateMission(missionId, payload),
    onSuccess: () => invalidateOperatorData(),
  });
  const manualMutation = useMutation({
    mutationFn: ({
      id,
      status,
      counts,
    }: {
      id: string;
      status: 'passed' | 'failed';
      counts?: { tasks_total?: number; tasks_correct?: number };
    }) => applyManualDecision(id, status, counts),
    onSuccess: () => invalidateOperatorData(),
  });
  const markReviewMutation = useMutation({
    mutationFn: ({ reviewId, passed }: { reviewId: string; passed: boolean }) =>
      markReviewResult(reviewId, passed),
    onSuccess: () => invalidateOperatorData(),
  });
  const scoreMutation = useMutation({
    mutationFn: () =>
      recordScoreEvent(studentId ?? '', {
        subject: scoreDraft.subject as 'math_profile' | 'informatics',
        score: Number(scoreDraft.score),
        kind: scoreDraft.kind,
        occurred_on: normalizeOptional(scoreDraft.occurred_on),
        note: normalizeOptional(scoreDraft.note),
      }),
    onSuccess: () => {
      setScoreDraft((current) => ({ ...current, score: '80', occurred_on: '', note: '' }));
      void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
    },
  });
  const noteMutation = useMutation({
    mutationFn: () =>
      publishMentorNote(studentId ?? '', {
        body: noteDraft.body,
        topic_id: normalizeOptional(noteDraft.topic_id),
      }),
    onSuccess: () => {
      setNoteDraft({ body: '', topic_id: '' });
      void queryClient.invalidateQueries({ queryKey: ['dashboard', studentId] });
    },
  });

  function submitCreateMission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createMissionMutation.mutate({
      subject: createDraft.subject,
      title: createDraft.title.trim(),
      instructions: createDraft.instructions?.trim() ?? '',
      threshold_percent: Number(createDraft.threshold_percent ?? 80),
      due_date: normalizeOptional(createDraft.due_date ?? ''),
      topic_id: normalizeOptional(createDraft.topic_id ?? ''),
      task_id: normalizeOptional(createDraft.task_id ?? ''),
    });
  }

  function submitUpdateMission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedMission || !selectedMissionDraft) return;
    updateMissionMutation.mutate({
      missionId: selectedMission.id,
      payload: {
        subject: selectedMissionDraft.subject,
        title: selectedMissionDraft.title.trim(),
        instructions: selectedMissionDraft.instructions?.trim() ?? '',
        threshold_percent: Number(selectedMissionDraft.threshold_percent ?? 80),
        due_date: normalizeOptional(selectedMissionDraft.due_date ?? ''),
        topic_id: normalizeOptional(selectedMissionDraft.topic_id ?? ''),
        task_id: normalizeOptional(selectedMissionDraft.task_id ?? ''),
      },
    });
  }

  return (
    <section>
      <div className="pageHeader">
        <h1>Оператор</h1>
        <p>Создание миссий, решения по проверкам, score events и заметки.</p>
      </div>
      {studentQuery.error || missionsQuery.error || manualQuery.error || reviewsQuery.error ? (
        <div className="state stateError">
          {errorMessage(studentQuery.error || missionsQuery.error || manualQuery.error || reviewsQuery.error)}
        </div>
      ) : null}

      <div className="panel">
        <h2>Новая миссия</h2>
        <form className="formGrid" onSubmit={submitCreateMission}>
          <label>
            <span>Предмет</span>
            <select
              value={createDraft.subject}
              onChange={(event) => setCreateDraft((current) => ({ ...current, subject: event.target.value as MissionDraft['subject'] }))}
            >
              <option value="math_profile">Профматематика</option>
              <option value="informatics">Информатика</option>
            </select>
          </label>
          <label>
            <span>Порог, %</span>
            <input type="number" min="0" max="100" value={createDraft.threshold_percent ?? 80} onChange={(event) => setCreateDraft((current) => ({ ...current, threshold_percent: Number(event.target.value) }))} />
          </label>
          <label>
            <span>Дедлайн</span>
            <input type="date" value={createDraft.due_date ?? ''} onChange={(event) => setCreateDraft((current) => ({ ...current, due_date: event.target.value }))} />
          </label>
          <label>
            <span>Topic ID (необязательно)</span>
            <input value={createDraft.topic_id ?? ''} onChange={(event) => setCreateDraft((current) => ({ ...current, topic_id: event.target.value }))} />
          </label>
          <label>
            <span>Task ID (только approved)</span>
            <input value={createDraft.task_id ?? ''} onChange={(event) => setCreateDraft((current) => ({ ...current, task_id: event.target.value }))} />
          </label>
          <label className="fieldWide">
            <span>Название</span>
            <input value={createDraft.title} onChange={(event) => setCreateDraft((current) => ({ ...current, title: event.target.value }))} />
          </label>
          <label className="fieldWide">
            <span>Инструкция</span>
            <textarea value={createDraft.instructions ?? ''} onChange={(event) => setCreateDraft((current) => ({ ...current, instructions: event.target.value }))} />
          </label>
          <div className="formActions">
            <button type="submit" disabled={!studentId || !createDraft.title.trim() || createMissionMutation.isPending}>
              Создать миссию
            </button>
            {createMissionMutation.error ? <span className="stateError">{errorMessage(createMissionMutation.error)}</span> : null}
          </div>
        </form>
      </div>

      <div className="panel">
        <h2>Активные миссии</h2>
        {missions.length ? (
          <div className="tableList">
            {missions.map((mission) => (
              <button
                key={mission.id}
                className={mission.id === selectedMission?.id ? 'missionButton active' : 'missionButton'}
                type="button"
                onClick={() => { setSelectedMissionId(mission.id); setEditDraft(missionToDraft(mission)); }}
              >
                <strong>{mission.title}</strong>
                <span className="missionMeta">{mission.subject} · порог {mission.threshold_percent}%</span>
              </button>
            ))}
          </div>
        ) : (
          <p className="muted">Активных миссий нет.</p>
        )}
        {selectedMission && selectedMissionDraft ? (
          <>
            <h2 style={{ marginTop: 18 }}>Правка миссии</h2>
            <form className="formGrid" onSubmit={submitUpdateMission}>
              <label>
                <span>Порог, %</span>
                <input type="number" min="0" max="100" value={selectedMissionDraft.threshold_percent ?? 80} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), threshold_percent: Number(event.target.value) }))} />
              </label>
              <label>
                <span>Дедлайн</span>
                <input type="date" value={selectedMissionDraft.due_date ?? ''} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), due_date: event.target.value }))} />
              </label>
              <label>
                <span>Topic ID</span>
                <input value={selectedMissionDraft.topic_id ?? ''} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), topic_id: event.target.value }))} />
              </label>
              <label>
                <span>Task ID</span>
                <input value={selectedMissionDraft.task_id ?? ''} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), task_id: event.target.value }))} />
              </label>
              <label className="fieldWide">
                <span>Название</span>
                <input value={selectedMissionDraft.title} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), title: event.target.value }))} />
              </label>
              <label className="fieldWide">
                <span>Инструкция</span>
                <textarea value={selectedMissionDraft.instructions ?? ''} onChange={(event) => setEditDraft((current) => ({ ...(current ?? missionToDraft(selectedMission)), instructions: event.target.value }))} />
              </label>
              <div className="formActions">
                <button type="submit" disabled={updateMissionMutation.isPending}>Сохранить</button>
                {updateMissionMutation.error ? <span className="stateError">{errorMessage(updateMissionMutation.error)}</span> : null}
              </div>
            </form>
          </>
        ) : null}
      </div>

      <div className="panel">
        <h2>Ручная проверка</h2>
        {manualQuery.data?.length ? (
          <div className="tableList">
            {manualQuery.data.map((item) => {
              const counts = manualCounts[item.id] ?? EMPTY_COUNTS;
              const partial = countsPartiallyFilled(counts);
              return (
                <article className="tableRow" key={item.id}>
                  <div>
                    <strong>{item.mission_title}</strong>
                    <span>{item.feedback}</span>
                    {item.tasks_total !== null && item.tasks_correct !== null ? (
                      <small>зачтено {item.tasks_correct}/{item.tasks_total}</small>
                    ) : null}
                  </div>
                  <div className="rowActions">
                    <input
                      type="number"
                      min="0"
                      placeholder="всего"
                      value={counts.tasks_total}
                      onChange={(event) => setManualCounts((current) => ({ ...current, [item.id]: { ...counts, tasks_total: event.target.value } }))}
                    />
                    <input
                      type="number"
                      min="0"
                      placeholder="верно"
                      value={counts.tasks_correct}
                      onChange={(event) => setManualCounts((current) => ({ ...current, [item.id]: { ...counts, tasks_correct: event.target.value } }))}
                    />
                    <button
                      disabled={manualMutation.isPending || partial}
                      onClick={() => manualMutation.mutate({ id: item.id, status: 'passed', counts: parseCounts(counts) })}
                      type="button"
                    >
                      Зачесть
                    </button>
                    <button
                      className="buttonSecondary"
                      disabled={manualMutation.isPending || partial}
                      onClick={() => manualMutation.mutate({ id: item.id, status: 'failed', counts: parseCounts(counts) })}
                      type="button"
                    >
                      В повтор
                    </button>
                    {partial ? <small className="muted">Заполните оба поля или оставьте оба пустыми.</small> : null}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <p className="muted">Очередь ручной проверки пуста.</p>
        )}
        {manualMutation.error ? <p className="stateError">{errorMessage(manualMutation.error)}</p> : null}
      </div>

      <div className="panel">
        <h2>Решения по повторам</h2>
        {reviewsQuery.data?.length ? (
          <div className="tableList">
            {reviewsQuery.data.map((item) => (
              <article className="tableRow" key={item.id}>
                <div>
                  <strong>{item.topic_title}</strong>
                  <span>{item.subject} · {new Date(item.due_date).toLocaleDateString('ru-RU')} · {item.status}</span>
                </div>
                <div className="rowActions">
                  <button disabled={markReviewMutation.isPending} onClick={() => markReviewMutation.mutate({ reviewId: item.id, passed: true })} type="button">Зачёт</button>
                  <button className="buttonSecondary" disabled={markReviewMutation.isPending} onClick={() => markReviewMutation.mutate({ reviewId: item.id, passed: false })} type="button">В работу</button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <p className="muted">Решений по повторам пока нет.</p>
        )}
        {markReviewMutation.error ? <p className="stateError">{errorMessage(markReviewMutation.error)}</p> : null}
      </div>

      <div className="panel">
        <h2>Score event</h2>
        <form className="formGrid" onSubmit={(event) => { event.preventDefault(); scoreMutation.mutate(); }}>
          <label>
            <span>Предмет</span>
            <select value={scoreDraft.subject} onChange={(event) => setScoreDraft((current) => ({ ...current, subject: event.target.value }))}>
              <option value="math_profile">Профматематика</option>
              <option value="informatics">Информатика</option>
            </select>
          </label>
          <label>
            <span>Балл</span>
            <input type="number" min="0" max="100" value={scoreDraft.score} onChange={(event) => setScoreDraft((current) => ({ ...current, score: event.target.value }))} />
          </label>
          <label className="fieldWide">
            <span>Тип</span>
            <select value={scoreDraft.kind} onChange={(event) => setScoreDraft((current) => ({ ...current, kind: event.target.value }))}>
              <option value="exam_variant">exam_variant — полный вариант</option>
              <option value="exam_like_slice">exam_like_slice — контрольный срез</option>
              <option value="weekly_variant">weekly_variant — недельный вариант</option>
            </select>
          </label>
          <p className="formHint">
            Все типы двигают текущий балл (§11). Диагностические срезы (topic_check) — это попытки/evidence, а не score event.
          </p>
          <label>
            <span>Дата</span>
            <input type="date" value={scoreDraft.occurred_on} onChange={(event) => setScoreDraft((current) => ({ ...current, occurred_on: event.target.value }))} />
          </label>
          <label className="fieldWide">
            <span>Заметка</span>
            <textarea value={scoreDraft.note} onChange={(event) => setScoreDraft((current) => ({ ...current, note: event.target.value }))} />
          </label>
          <div className="formActions">
            <button type="submit" disabled={!studentId || scoreMutation.isPending}>Записать score event</button>
            {scoreMutation.error ? <span className="stateError">{errorMessage(scoreMutation.error)}</span> : null}
          </div>
        </form>
      </div>

      <div className="panel">
        <h2>Заметка наставника</h2>
        <form className="formGrid" onSubmit={(event) => { event.preventDefault(); noteMutation.mutate(); }}>
          <label>
            <span>Topic ID (необязательно)</span>
            <input value={noteDraft.topic_id} onChange={(event) => setNoteDraft((current) => ({ ...current, topic_id: event.target.value }))} />
          </label>
          <label className="fieldWide">
            <span>Текст для ученика</span>
            <textarea value={noteDraft.body} onChange={(event) => setNoteDraft((current) => ({ ...current, body: event.target.value }))} />
          </label>
          <div className="formActions">
            <button type="submit" disabled={!studentId || !noteDraft.body.trim() || noteMutation.isPending}>Опубликовать</button>
            {noteMutation.error ? <span className="stateError">{errorMessage(noteMutation.error)}</span> : null}
          </div>
        </form>
      </div>
    </section>
  );
}
