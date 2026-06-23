import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  drawSlice,
  errorMessage,
  getCurrentStudent,
  getProgram,
  gradeSlice,
  type SliceResult,
  type SliceTask,
  type Subject,
} from '../shared/api/client';

const SUBJECT_OPTIONS: Array<{ value: Subject; label: string }> = [
  { value: 'math_profile', label: 'Профматематика' },
  { value: 'informatics', label: 'Информатика' },
];

function subjectLabel(subject: Subject): string {
  return SUBJECT_OPTIONS.find((option) => option.value === subject)?.label ?? subject;
}

export function SlicePage() {
  const studentQuery = useQuery({ queryKey: ['student', 'current'], queryFn: getCurrentStudent });
  const studentId = studentQuery.data?.id;

  const [subject, setSubject] = useState<Subject>('math_profile');
  const [topicId, setTopicId] = useState<string>('');
  const [size, setSize] = useState(8);
  const [tasks, setTasks] = useState<SliceTask[] | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SliceResult | null>(null);

  const programQuery = useQuery({
    queryKey: ['program', studentId],
    queryFn: () => getProgram(studentId ?? ''),
    enabled: !!studentId,
  });
  const topicOptions = (programQuery.data ?? [])
    .flatMap((phase) => phase.topics)
    .filter((topic) => topic.subject === subject && topic.tasks_in_bank > 0)
    .sort((a, b) => a.topic_title.localeCompare(b.topic_title));
  const selectedTopic = topicOptions.find((topic) => topic.topic_id === topicId);
  const sliceLabel = selectedTopic ? selectedTopic.topic_title : subjectLabel(subject);

  const drawMutation = useMutation({
    mutationFn: () => drawSlice(studentId ?? '', subject, size, topicId || undefined),
    onSuccess: (data) => {
      setTasks(data.items);
      setAnswers({});
      setResult(null);
    },
  });
  const gradeMutation = useMutation({
    mutationFn: () =>
      gradeSlice(studentId ?? '', {
        subject,
        items: (tasks ?? []).map((task) => ({
          task_id: task.task_id,
          answer_text: answers[task.task_id] ?? '',
        })),
      }),
    onSuccess: (data) => setResult(data),
  });

  const correctById = new Map((result?.items ?? []).map((item) => [item.task_id, item.correct]));
  const allAnswered = (tasks ?? []).every((task) => (answers[task.task_id] ?? '').trim() !== '');

  function resetSlice() {
    setTasks(null);
    setResult(null);
    setAnswers({});
  }

  return (
    <section>
      <div className="pageHeader">
        <h1>Срез знаний</h1>
        <p>Реши набор задач из банка — ответы проверятся сразу по ключу. Это диагностика: текущий балл она не двигает.</p>
      </div>
      {studentQuery.error ? <div className="state stateError">{errorMessage(studentQuery.error)}</div> : null}

      {!tasks ? (
        <div className="panel">
          <form className="formGrid" onSubmit={(event) => { event.preventDefault(); drawMutation.mutate(); }}>
            <label>
              <span>Предмет</span>
              <select
                value={subject}
                onChange={(event) => { setSubject(event.target.value as Subject); setTopicId(''); }}
              >
                {SUBJECT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label>
              <span>Тема</span>
              <select value={topicId} onChange={(event) => setTopicId(event.target.value)}>
                <option value="">Вся тема (случайно)</option>
                {topicOptions.map((topic) => (
                  <option key={topic.topic_id} value={topic.topic_id}>
                    {topic.topic_title} ({topic.tasks_in_bank})
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Сколько задач</span>
              <select value={size} onChange={(event) => setSize(Number(event.target.value))}>
                <option value={5}>5</option>
                <option value={8}>8</option>
                <option value={10}>10</option>
              </select>
            </label>
            <div className="formActions">
              <button type="submit" disabled={!studentId || drawMutation.isPending}>Начать срез</button>
              {drawMutation.error ? <span className="stateError">{errorMessage(drawMutation.error)}</span> : null}
            </div>
          </form>
        </div>
      ) : null}

      {tasks && !result ? (
        <div className="panel">
          <h2>{sliceLabel} · {tasks.length} задач</h2>
          {tasks.length ? (
            <div className="tableList">
              {tasks.map((task, index) => (
                <div key={task.task_id} className="sliceTask">
                  <p className="sliceStatement">{index + 1}. {task.statement}</p>
                  <input
                    value={answers[task.task_id] ?? ''}
                    placeholder="Ответ"
                    onChange={(event) => setAnswers((current) => ({ ...current, [task.task_id]: event.target.value }))}
                  />
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">В банке нет задач с готовым ответом для этого предмета.</p>
          )}
          <div className="formActions" style={{ marginTop: 14 }}>
            <button type="button" disabled={!allAnswered || gradeMutation.isPending || !tasks.length} onClick={() => gradeMutation.mutate()}>
              Завершить срез
            </button>
            <button type="button" className="buttonSecondary" onClick={resetSlice}>Отмена</button>
            {gradeMutation.error ? <span className="stateError">{errorMessage(gradeMutation.error)}</span> : null}
          </div>
        </div>
      ) : null}

      {result ? (
        <div className="panel">
          <h2>
            Результат: {result.tasks_correct}/{result.tasks_total} · {result.percent}%{' '}
            <span className={`badge ${result.passed ? 'badge--confirmed' : 'badge--back'}`}>
              {result.passed ? 'Зачёт' : 'Недобор'}
            </span>
          </h2>
          <div className="tableList">
            {(tasks ?? []).map((task, index) => (
              <article className="tableRow" key={task.task_id}>
                <div>
                  <span className="sliceStatement">{index + 1}. {task.statement}</span>
                  <small>Твой ответ: {answers[task.task_id]?.trim() || '—'}</small>
                </div>
                <div>
                  <span className={`badge ${correctById.get(task.task_id) ? 'badge--confirmed' : 'badge--back'}`}>
                    {correctById.get(task.task_id) ? 'верно' : 'неверно'}
                  </span>
                </div>
              </article>
            ))}
          </div>
          <div className="formActions" style={{ marginTop: 14 }}>
            <button type="button" onClick={resetSlice}>Новый срез</button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
