import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";
import data from "./data.json";

// Fonts ship in public/fonts (OFL), so a render needs no network.
const fonts: [string, string, string][] = [
  ["Newsreader", "Newsreader.woff2", "200 800"], ["Hanken Grotesk", "HankenGrotesk.woff2", "100 900"],
  ["IBM Plex Mono", "IBMPlexMono-400.woff2", "400"], ["IBM Plex Mono", "IBMPlexMono-500.woff2", "500"],
];
fonts.forEach(([family, file, weight]) => loadFont({ family, url: staticFile(`fonts/${file}`), weight }));
const serif = "Newsreader, Georgia, serif";
const sans = "'Hanken Grotesk', system-ui, sans-serif";
const mono = "'IBM Plex Mono', monospace";

const C = {
  paper: "#f6f3ec", sheet: "#fffdf8", ink: "#1b1a17", ink2: "#4a4740", ink3: "#8a857a", rule: "#e2ddd0",
  red: "#c8371f", redWash: "#f7e1d9", green: "#1f7a52", greenWash: "#dcefe4",
};
const ease = Easing.bezier(0.65, 0, 0.35, 1);
const out = Easing.bezier(0.16, 1, 0.3, 1);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// One world, one camera. Every scene is a place on this sheet; the camera never cuts.
const W = { request: { x: 160, y: 160, w: 1500 }, plain: { x: 160, y: 900, w: 1500 }, brogue: { x: 1860, y: 900, w: 1500 },
  chart: { x: 1860, y: 1720, w: 1500 }, end: { x: 860, y: 2580, w: 1800 } };

// Camera keyframes: second, world-x and world-y of the view centre, width of world shown.
const SHOTS: [number, number, number, number][] = [
  [0, 910, 330, 1500],      // close on the request
  [3.6, 910, 360, 1700],
  [5.0, 910, 1340, 1950],   // glide down to the unaided answer
  [10.4, 910, 1350, 1900],
  [11.8, 1760, 1250, 3400], // pull out: both answers side by side
  [13.2, 1760, 1250, 3400],
  [14.6, 2610, 1170, 1700], // push into Brogue's answer
  [17.4, 2610, 1170, 1700],
  [19.0, 2610, 2110, 1750], // drop to the benchmark
  [23.6, 2610, 2110, 1750],
  [25.4, 1760, 1550, 3900], // pull all the way out
  [26.4, 1760, 1650, 3900],
  [28.0, 1760, 2760, 1750], // settle on the install card
  [31.0, 1760, 2760, 1750],
];

const camera = (t: number) => {
  let i = 0;
  while (i < SHOTS.length - 2 && t > SHOTS[i + 1][0]) i++;
  const [t0, x0, y0, w0] = SHOTS[i];
  const [t1, x1, y1, w1] = SHOTS[i + 1];
  const p = interpolate(t, [t0, t1], [0, 1], { ...clamp, easing: ease });
  // zoom interpolates in log space so a pull-out feels even all the way
  return { x: x0 + (x1 - x0) * p, y: y0 + (y1 - y0) * p, w: Math.exp(Math.log(w0) + (Math.log(w1) - Math.log(w0)) * p) };
};

const Sheet: React.FC<{ x: number; y: number; w: number; children: React.ReactNode; tone?: "green" | "plain"; label: string; badge?: React.ReactNode }> =
  ({ x, y, w, children, tone, label, badge }) => (
    <div style={{ position: "absolute", left: x, top: y, width: w, background: C.sheet, borderRadius: 28, border: `2px solid ${tone === "green" ? C.green : C.rule}`,
      boxShadow: "0 2px 0 rgba(27,26,23,.04), 0 30px 60px -30px rgba(27,26,23,.35)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "30px 44px", borderBottom: `2px solid ${C.rule}` }}>
        <div style={{ font: `500 26px ${mono}`, letterSpacing: "0.14em", textTransform: "uppercase", color: tone === "green" ? C.green : C.ink3 }}>{label}</div>
        {badge}
      </div>
      <div style={{ padding: "36px 44px 44px" }}>{children}</div>
    </div>
  );

// Text revealed word by word between two times; marked phrases get a red strike drawn across them in turn.
const Prose: React.FC<{ text: string; marks?: string[]; t: number; from: number; to: number; strikeFrom?: number; strikeEach?: number; size?: number }> =
  ({ text, marks = [], t, from, to, strikeFrom = 0, strikeEach = 0.5, size = 40 }) => {
    const spans: { s: string; m: number }[] = [];
    let rest = text;
    while (rest.length) {
      let best = -1, at = rest.length;
      marks.forEach((q, k) => { const i = rest.indexOf(q); if (i >= 0 && i < at) { at = i; best = k; } });
      if (at > 0) spans.push({ s: rest.slice(0, at), m: -1 });
      if (best < 0) break;
      spans.push({ s: marks[best], m: best });
      rest = rest.slice(at + marks[best].length);
    }
    const total = text.length;
    let seen = 0;
    return (
      <div style={{ font: `400 ${size}px/1.5 ${serif}`, color: C.ink, whiteSpace: "pre-wrap" }}>
        {spans.map((sp, i) => {
          const start = seen / total;
          seen += sp.s.length;
          const shown = interpolate(t, [from + (to - from) * start, from + (to - from) * (seen / total) + 0.15], [0, 1], clamp);
          const strike = sp.m < 0 ? 0 : interpolate(t, [strikeFrom + sp.m * strikeEach, strikeFrom + sp.m * strikeEach + 0.45], [0, 100], { ...clamp, easing: out });
          return (
            <span key={i} style={{ opacity: shown, color: strike > 0 ? C.red : undefined, WebkitBoxDecorationBreak: "clone", boxDecorationBreak: "clone",
              backgroundImage: sp.m < 0 ? undefined : `linear-gradient(${C.red}, ${C.red}), linear-gradient(${C.redWash}, ${C.redWash})`,
              backgroundRepeat: "no-repeat", backgroundPosition: "0 58%, 0 0", backgroundSize: `${strike}% 4px, ${strike > 0 ? 100 : 0}% 100%`, borderRadius: 4 }}>{sp.s}</span>
          );
        })}
      </div>
    );
  };

const Badge: React.FC<{ n: number; good?: boolean; show: number }> = ({ n, good, show }) => (
  <div style={{ opacity: show, font: `600 30px ${sans}`, padding: "12px 20px", borderRadius: 12, background: good ? C.greenWash : C.redWash, color: good ? C.green : C.red }}>
    {n} made up
  </div>
);

export const Film: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const t = frame / fps;
  const cam = camera(t);
  const zoom = width / cam.w;
  const marks: string[] = data.plain.made_up;
  const strikeFrom = 7.0, strikeEach = Math.min(0.55, 2.6 / Math.max(marks.length, 1));
  const struck = marks.filter((_, k) => t > strikeFrom + k * strikeEach + 0.2).length;
  const max = Math.ceil(Math.max(...data.rows.map((r) => r.hi)));
  const fadeIn = (a: number) => interpolate(t, [a, a + 0.6], [0, 1], { ...clamp, easing: out });

  return (
    <AbsoluteFill style={{ background: C.paper, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 3600, height: 3200, transformOrigin: "0 0",
        translate: `${width / 2 - cam.x * zoom}px ${height / 2 - cam.y * zoom}px`, scale: `${zoom}` }}>
        {/* faint ruled lines: the galley the whole film lives on */}
        <div style={{ position: "absolute", inset: 0, backgroundImage: `repeating-linear-gradient(0deg, transparent 0 59px, ${C.rule} 59px 60px)`, opacity: 0.45 }} />

        <Sheet {...W.request} label="The request · everything the model was told">
          <Prose text={data.request} t={t} from={0.3} to={2.6} size={46} />
          <div style={{ marginTop: 26, font: `400 30px ${sans}`, color: C.ink2, opacity: fadeIn(2.6) }}>Reader: {data.reader}</div>
        </Sheet>

        <Sheet {...W.plain} label="No skill" badge={<Badge n={struck} show={fadeIn(strikeFrom)} />}>
          <Prose text={data.plain.text} marks={marks} t={t} from={4.6} to={6.8} strikeFrom={strikeFrom} strikeEach={strikeEach} size={36} />
        </Sheet>

        <Sheet {...W.brogue} label="Same model, with Brogue" tone="green" badge={<Badge n={0} good show={fadeIn(13.4)} />}>
          <Prose text={data.brogue.text} t={t} from={12.4} to={13.6} size={36} />
          <div style={{ marginTop: 30, display: "flex", gap: 16, alignItems: "center", font: `600 30px ${sans}`, color: C.green, opacity: fadeIn(15.2) }}>
            <svg width="34" height="34" viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke={C.green} strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray="30" strokeDashoffset={interpolate(t, [15.2, 15.9], [30, 0], clamp)} /></svg>
            Every sentence traces to the request.
          </div>
        </Sheet>

        <div style={{ opacity: fadeIn(17.4) }}><Sheet {...W.chart} label={`Made-up details per text · ${data.texts} texts, ${data.tasks} tasks`}>
          {data.rows.map((r, i) => {
            const grow = interpolate(t, [18.4 + i * 0.12, 19.4 + i * 0.12], [0, 1], { ...clamp, easing: out });
            const x = (v: number) => 340 + (1040 * v) / max;
            return (
              <div key={r.name} style={{ position: "relative", height: 74 }}>
                <div style={{ position: "absolute", left: 0, width: 300, top: 16, textAlign: "right", font: `${r.ours ? 700 : 400} 32px ${sans}`, color: r.ours ? C.ink : C.ink2 }}>{r.name}</div>
                <div style={{ position: "absolute", left: x(r.lo), top: 30, height: 12, width: (x(r.hi) - x(r.lo)) * grow, borderRadius: 6, background: r.ours ? C.green : C.ink3, opacity: 0.3 }} />
                <div style={{ position: "absolute", left: x(r.mean * grow) - 13, top: 23, width: 26, height: 26, borderRadius: 13, background: r.ours ? C.green : C.ink3, border: `4px solid ${C.sheet}` }} />
                <div style={{ position: "absolute", left: x(r.hi) + 22, top: 16, font: `600 32px ${mono}`, color: r.ours ? C.green : C.ink2, opacity: fadeIn(19.4 + i * 0.12) }}>{r.mean.toFixed(2)}</div>
              </div>
            );
          })}
          <div style={{ marginTop: 18, font: `400 26px ${sans}`, color: C.ink3, opacity: fadeIn(20.4) }}>Dots are means; bars are 95% intervals. Same model, every skill installed the same way.</div>
        </Sheet>
        </div>

        <div style={{ position: "absolute", left: W.end.x, top: W.end.y, width: W.end.w, textAlign: "center", opacity: fadeIn(26.2) }}>
          <div style={{ font: `500 92px/1.05 ${serif}`, letterSpacing: "-0.02em", color: C.ink, textWrap: "balance" }}>{data.headline}</div>
          <div style={{ marginTop: 26, font: `400 40px ${sans}`, color: C.ink2 }}>{data.sub}</div>
          <div style={{ display: "inline-block", marginTop: 46, padding: "28px 44px", borderRadius: 20, background: C.ink, color: C.paper, font: `500 44px ${mono}` }}>
            <span style={{ color: "#5fd49c" }}>$ </span>{data.install}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
