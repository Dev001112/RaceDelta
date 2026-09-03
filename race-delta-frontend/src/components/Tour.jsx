import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { getTour } from "../lib/tours";

/*
  Guided page tour with a start-light gantry as its progress indicator.
  - Pages mark targets with data-tour="id"; steps live in lib/tours.js.
  - Auto-starts once per page (localStorage), replays via startTour() (Guide button).
  - Keyboard: Esc skips, ←/→ navigate. Respects reduced motion.
*/

const PAD = 8;
const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const storageKey = (key) => `racedelta.tour.${key}`;

export const startTour = () => window.dispatchEvent(new CustomEvent("racedelta:tour"));

function StartLights({ step, total }) {
  const lit = Math.ceil(((step + 1) / total) * 5);
  return (
    <div className="tour-lights" aria-hidden="true">
      {[0, 1, 2, 3, 4].map((n) => <span key={n} className={`tour-light ${n < lit ? "on" : ""}`} />)}
    </div>
  );
}

export default function Tour() {
  const { pathname } = useLocation();
  const tour = useMemo(() => getTour(pathname), [pathname]);
  const [steps, setSteps] = useState([]);
  const [i, setI] = useState(0);
  const [rect, setRect] = useState(null);
  const open = steps.length > 0;
  const step = steps[i];

  const begin = useCallback(() => {
    if (!tour) return;
    const available = tour.steps.filter((s) => !s.target || document.querySelector(`[data-tour="${s.target}"]`));
    if (!available.length) return;
    setI(0);
    setSteps(available);
  }, [tour]);

  const finish = useCallback(() => {
    try { if (tour) localStorage.setItem(storageKey(tour.key), "done"); } catch { /* storage unavailable */ }
    setSteps([]);
    setI(0);
    setRect(null);
  }, [tour]);

  // auto-start once per page, after its data has had a moment to render
  useEffect(() => {
    setSteps([]); setI(0); setRect(null);
    if (!tour) return;
    if (new URLSearchParams(window.location.search).has("notour")) return;   // ?notour suppresses auto-start
    let seen = false;
    try { seen = localStorage.getItem(storageKey(tour.key)) === "done"; } catch { /* ignore */ }
    if (seen) return;
    const t = setTimeout(begin, 1400);
    return () => clearTimeout(t);
  }, [tour, begin]);

  useEffect(() => {
    window.addEventListener("racedelta:tour", begin);
    return () => window.removeEventListener("racedelta:tour", begin);
  }, [begin]);

  // measure the current target (and follow it through scroll / resize)
  useLayoutEffect(() => {
    if (!step) return;
    const el = step.target ? document.querySelector(`[data-tour="${step.target}"]`) : null;
    const measure = () => {
      if (!el) { setRect(null); return; }
      const r = el.getBoundingClientRect();
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height, bottom: r.bottom });
    };
    if (el) el.scrollIntoView({ block: "center", inline: "nearest", behavior: reduced() ? "auto" : "smooth" });
    measure();
    const t = setTimeout(measure, 450);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => { clearTimeout(t); window.removeEventListener("resize", measure); window.removeEventListener("scroll", measure, true); };
  }, [step]);

  const next = useCallback(() => { if (i + 1 < steps.length) setI(i + 1); else finish(); }, [i, steps.length, finish]);
  const back = useCallback(() => setI((n) => Math.max(0, n - 1)), []);

  useEffect(() => {
    if (!open) return;
    const h = (e) => {
      if (e.key === "Escape") finish();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") back();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, finish, next, back]);

  if (!open || !step) return null;

  const W = Math.min(400, window.innerWidth - 24);
  let cardStyle;
  if (rect) {
    const left = Math.min(Math.max(12, rect.left), Math.max(12, window.innerWidth - W - 12));
    const spaceBelow = window.innerHeight - (rect.bottom + PAD + 14);
    cardStyle = spaceBelow > 260 || rect.top < 260
      ? { top: rect.bottom + PAD + 14, left, width: W }
      : { bottom: window.innerHeight - (rect.top - PAD - 14), left, width: W };
  } else {
    cardStyle = { top: "50%", left: "50%", transform: "translate(-50%, -50%)", width: W };
  }
  const last = i + 1 === steps.length;

  return createPortal(
    <div role="dialog" aria-modal="true" aria-label="Page guide">
      {rect
        ? <div className="tour-spot" style={{ top: rect.top - PAD, left: rect.left - PAD, width: rect.width + 2 * PAD, height: rect.height + 2 * PAD }} />
        : <div className="tour-dim" onClick={finish} />}
      <div className="tour-card" style={cardStyle}>
        <div className="tour-top">
          <span className="eyebrow eyebrow-red">Page guide · step {i + 1} of {steps.length}</span>
          <StartLights step={i} total={steps.length} />
        </div>
        <h3 className="tour-title">{step.title}</h3>
        <p className="tour-body">{step.body}</p>
        <div className="tour-actions">
          <button type="button" className="btn-ghost" onClick={finish}>Skip guide</button>
          <div className="tour-nav">
            {i > 0 && <button type="button" className="btn-ghost" onClick={back}>Back</button>}
            <button type="button" className="btn-primary" onClick={next} autoFocus>{last ? "Lights out" : "Next"}</button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
