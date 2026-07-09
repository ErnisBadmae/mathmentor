import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { errorMessage, getTopicTheory, type TheoryCard, type TheoryVisual } from '../shared/api/client';

type Point = { x: number; y: number };
type VectorSpec = Point & { name: string; color: string };

function numberParam(params: Record<string, unknown>, key: string, fallback: number): number {
  const value = params[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function vectorSpecs(params: Record<string, unknown>): VectorSpec[] {
  const raw = Array.isArray(params.vectors) ? params.vectors : [];
  const parsed = raw
    .map((item, index) => {
      if (!item || typeof item !== 'object') return null;
      const source = item as Record<string, unknown>;
      const x = typeof source.x === 'number' ? source.x : 0;
      const y = typeof source.y === 'number' ? source.y : 0;
      const name = typeof source.name === 'string' ? source.name : `v${index + 1}`;
      const color = typeof source.color === 'string' ? source.color : '#2d6cdf';
      return { x, y, name, color };
    })
    .filter((item): item is VectorSpec => item !== null);

  return parsed.length
    ? parsed
    : [
        { name: 'a', x: 3, y: 2, color: '#2d6cdf' },
        { name: 'b', x: 1, y: 3, color: '#d05a36' },
      ];
}

function VectorVisual({ visual }: { visual: TheoryVisual }) {
  const params = visual.params;
  const vectors = vectorSpecs(params);
  const a = vectors[0];
  const b = vectors[1] ?? { name: 'b', x: 1, y: 3, color: '#d05a36' };
  const sum = { x: a.x + b.x, y: a.y + b.y };
  const width = 640;
  const height = 360;
  const xMin = -1;
  const xMax = Math.max(5, sum.x + 1);
  const yMin = -1;
  const yMax = Math.max(6, sum.y + 1);
  const pad = 42;
  const plotW = width - pad * 2;
  const plotH = height - pad * 2;
  const sx = (x: number) => pad + ((x - xMin) / (xMax - xMin)) * plotW;
  const sy = (y: number) => height - pad - ((y - yMin) / (yMax - yMin)) * plotH;

  function arrow(start: Point, end: Point, color: string, className?: string) {
    return (
      <line
        className={className}
        x1={sx(start.x)}
        y1={sy(start.y)}
        x2={sx(end.x)}
        y2={sy(end.y)}
        stroke={color}
        strokeLinecap="round"
        strokeWidth="4"
        markerEnd="url(#vector-arrow)"
      />
    );
  }

  return (
    <svg className="visualSvg" role="img" aria-label={visual.alt_text} viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <marker id="vector-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke" />
        </marker>
      </defs>
      {Array.from({ length: Math.floor(xMax - xMin) + 1 }, (_, index) => xMin + index).map((x) => (
        <line className="visualGridLine" key={`x-${x}`} x1={sx(x)} y1={sy(yMin)} x2={sx(x)} y2={sy(yMax)} />
      ))}
      {Array.from({ length: Math.floor(yMax - yMin) + 1 }, (_, index) => yMin + index).map((y) => (
        <line className="visualGridLine" key={`y-${y}`} x1={sx(xMin)} y1={sy(y)} x2={sx(xMax)} y2={sy(y)} />
      ))}
      <line className="visualAxis" x1={sx(xMin)} y1={sy(0)} x2={sx(xMax)} y2={sy(0)} />
      <line className="visualAxis" x1={sx(0)} y1={sy(yMin)} x2={sx(0)} y2={sy(yMax)} />
      {arrow({ x: 0, y: 0 }, a, a.color)}
      {arrow(a, sum, b.color)}
      {arrow({ x: 0, y: 0 }, sum, '#23835f', 'visualStrongArrow')}
      <circle cx={sx(0)} cy={sy(0)} r="4" fill="#17201a" />
      <circle cx={sx(a.x)} cy={sy(a.y)} r="4" fill={a.color} />
      <circle cx={sx(sum.x)} cy={sy(sum.y)} r="4" fill="#23835f" />
      <text className="visualLabel" x={sx(a.x) - 24} y={sy(a.y) - 12}>
        {a.name}
      </text>
      <text className="visualLabel" x={sx((a.x + sum.x) / 2) + 10} y={sy((a.y + sum.y) / 2) - 12}>
        {b.name}
      </text>
      <text className="visualLabel visualLabelStrong" x={sx(sum.x) + 10} y={sy(sum.y) + 4}>
        {a.name}+{b.name}
      </text>
    </svg>
  );
}

function VectorDotProductVisual() {
  const width = 640;
  const height = 360;
  const origin = { x: 120, y: 245 };
  const aEnd = { x: 300, y: 155 };
  const bEnd = { x: 240, y: 75 };

  return (
    <svg className="visualSvg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Скалярное произведение векторов в координатах">
      <defs>
        <marker id="arrowHeadDot" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L9,3 z" fill="#26352e" />
        </marker>
      </defs>
      {Array.from({ length: 8 }, (_, i) => (
        <line key={`v-${i}`} className="visualGridLine" x1={60 + i * 40} x2={60 + i * 40} y1="45" y2="285" />
      ))}
      {Array.from({ length: 7 }, (_, i) => (
        <line key={`h-${i}`} className="visualGridLine" x1="60" x2="340" y1={45 + i * 40} y2={45 + i * 40} />
      ))}
      <line className="visualAxis" x1="60" x2="350" y1={origin.y} y2={origin.y} />
      <line className="visualAxis" x1={origin.x} x2={origin.x} y1="45" y2="285" />
      <line
        x1={origin.x}
        y1={origin.y}
        x2={aEnd.x}
        y2={aEnd.y}
        stroke="#2d6cdf"
        strokeWidth="5"
        strokeLinecap="round"
        markerEnd="url(#arrowHeadDot)"
      />
      <line
        x1={origin.x}
        y1={origin.y}
        x2={bEnd.x}
        y2={bEnd.y}
        stroke="#d05a36"
        strokeWidth="5"
        strokeLinecap="round"
        markerEnd="url(#arrowHeadDot)"
      />
      <text className="visualLabel" x={aEnd.x + 10} y={aEnd.y + 5}>a=(x1; y1)</text>
      <text className="visualLabel" x={bEnd.x + 10} y={bEnd.y - 8}>b=(x2; y2)</text>
      <text className="visualFormula" x="385" y="120">a·b = x1·x2 + y1·y2</text>
      <text className="visualLabel" x="386" y="160">перемножь координаты парами</text>
      <text className="visualLabel visualLabelStrong" x="386" y="198">результат — число</text>
    </svg>
  );
}

function DerivativeVisual({ visual }: { visual: TheoryVisual }) {
  const params = visual.params;
  const width = 640;
  const height = 360;
  const pad = 44;
  const xMin = numberParam(params, 'x_min', -1);
  const xMax = numberParam(params, 'x_max', 4);
  const yMin = numberParam(params, 'y_min', -1);
  const yMax = numberParam(params, 'y_max', 7);
  const x0 = numberParam(params, 'x0', 2);
  const slope = numberParam(params, 'slope', 2);
  const f = (x: number) => x * x - 2 * x + 1;
  const y0 = f(x0);
  const sx = (x: number) => pad + ((x - xMin) / (xMax - xMin)) * (width - pad * 2);
  const sy = (y: number) => height - pad - ((y - yMin) / (yMax - yMin)) * (height - pad * 2);
  const curve = Array.from({ length: 80 }, (_, index) => {
    const x = xMin + ((xMax - xMin) * index) / 79;
    return `${sx(x)},${sy(f(x))}`;
  }).join(' ');
  const tangentStart = { x: xMin, y: y0 + slope * (xMin - x0) };
  const tangentEnd = { x: xMax, y: y0 + slope * (xMax - x0) };

  return (
    <svg className="visualSvg" role="img" aria-label={visual.alt_text} viewBox={`0 0 ${width} ${height}`}>
      {Array.from({ length: Math.floor(xMax - xMin) + 1 }, (_, index) => xMin + index).map((x) => (
        <line className="visualGridLine" key={`x-${x}`} x1={sx(x)} y1={sy(yMin)} x2={sx(x)} y2={sy(yMax)} />
      ))}
      {Array.from({ length: Math.floor(yMax - yMin) + 1 }, (_, index) => yMin + index).map((y) => (
        <line className="visualGridLine" key={`y-${y}`} x1={sx(xMin)} y1={sy(y)} x2={sx(xMax)} y2={sy(y)} />
      ))}
      <line className="visualAxis" x1={sx(xMin)} y1={sy(0)} x2={sx(xMax)} y2={sy(0)} />
      <line className="visualAxis" x1={sx(0)} y1={sy(yMin)} x2={sx(0)} y2={sy(yMax)} />
      <polyline className="visualCurve" points={curve} />
      <line className="visualTangent" x1={sx(tangentStart.x)} y1={sy(tangentStart.y)} x2={sx(tangentEnd.x)} y2={sy(tangentEnd.y)} />
      <circle className="visualPoint" cx={sx(x0)} cy={sy(y0)} r="6" />
      <text className="visualLabel visualLabelStrong" x={sx(x0) + 12} y={sy(y0) - 12}>
        x0={x0}
      </text>
      <text className="visualLabel" x={sx(xMin) + 18} y={sy(tangentStart.y) - 12}>
        k=f'(x0)={slope}
      </text>
      <text className="visualLabel" x={sx(xMax) - 120} y={sy(f(xMax)) + 24}>
        y=x^2-2x+1
      </text>
    </svg>
  );
}

function VisualRenderer({ visual }: { visual: TheoryVisual }) {
  if (visual.kind === 'vector_2d') return <VectorVisual visual={visual} />;
  if (visual.kind === 'vector_dot_product') return <VectorDotProductVisual />;
  if (visual.kind === 'derivative_tangent') return <DerivativeVisual visual={visual} />;
  return <div className="state">Визуальный шаблон пока не поддержан: {visual.kind}</div>;
}

function TheoryCardView({ card }: { card: TheoryCard }) {
  return (
    <article className="theoryCard">
      <div className="theoryText">
        <span className="badge badge--visual">Визуализация</span>
        <h2>{card.title}</h2>
        {card.body_md.split('\n').map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
      </div>
      <div className="visualFrame">
        <VisualRenderer visual={card.visual} />
      </div>
    </article>
  );
}

export function TheoryPage() {
  const { topicId } = useParams();
  const query = useQuery({
    queryKey: ['topic-theory', topicId],
    queryFn: () => getTopicTheory(topicId ?? ''),
    enabled: Boolean(topicId),
  });
  const firstCard = query.data?.[0];

  return (
    <section className="theoryPage">
      <div className="pageHeader">
        <Link className="buttonSecondary linkButton" to="/program">
          К программе
        </Link>
        <h1>{firstCard?.topic_title ?? 'Визуализация темы'}</h1>
        <p>Короткая опора перед самостоятельной попыткой: идея и рисунок без ответа к конкретной задаче.</p>
      </div>
      {query.error ? <div className="state stateError">{errorMessage(query.error)}</div> : null}
      {query.isLoading ? <div className="state">Загрузка...</div> : null}
      {query.data?.length === 0 ? <div className="state">Для этой темы пока нет визуальной карточки.</div> : null}
      <div className="theoryCards">{query.data?.map((card) => <TheoryCardView card={card} key={card.id} />)}</div>
    </section>
  );
}
