"use client";

// HoverExplain — the single page-dimming overlay every metric description + comparison surfaces
// through (Phase 75-05). Almost nothing on the report card is always-on prose: a coach hovers (or
// focuses) a dotted label and the page dims behind a positioned popover. Ported from the v3 concept
// mockup (report-card-concept-v3.html); React-native (no data-attribute string smuggling — the
// popover body is JSX).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";

const ExplainCtx = createContext(null);

function TagChip({ tag }) {
  const label = tag === "good" ? "better" : tag === "bad" ? "worse" : "changed";
  const bg =
    tag === "good"
      ? "bg-good"
      : tag === "bad"
        ? "bg-bad"
        : "bg-neutral";
  return (
    <span
      className={`rounded-full px-1.5 py-0.5 text-[8.5px] font-semibold uppercase tracking-wider text-black ${bg}`}
    >
      {label}
    </span>
  );
}

export function HoverExplainProvider({ children }) {
  const [payload, setPayload] = useState(null); // { title, tag, body, rect }
  const [pos, setPos] = useState(null); // { left, top } once measured
  const [mounted, setMounted] = useState(false);
  const popRef = useRef(null);

  useEffect(() => setMounted(true), []);

  const show = useCallback((p) => {
    setPos(null); // re-measure for the new anchor before revealing
    setPayload(p);
  }, []);
  const hide = useCallback(() => {
    setPayload(null);
    setPos(null);
  }, []);

  // Measure the popover against its anchor rect and clamp to the viewport, before paint so it never
  // flashes at the wrong spot. Prefer above the trigger; drop below when there is no room.
  useLayoutEffect(() => {
    if (!payload?.rect || !popRef.current) return;
    const r = payload.rect;
    const pr = popRef.current.getBoundingClientRect();
    let left = r.left + r.width / 2 - pr.width / 2;
    left = Math.max(12, Math.min(left, window.innerWidth - pr.width - 12));
    let top = r.top - pr.height - 10;
    if (top < 12) top = r.bottom + 10;
    setPos({ left, top });
  }, [payload]);

  return (
    <ExplainCtx.Provider value={{ show, hide }}>
      {children}
      {mounted &&
        createPortal(
          <>
            {/* scrim — visual only (pointer-events none), so hovering the trigger is never
                interrupted by it */}
            <div
              aria-hidden
              className={`fixed inset-0 z-40 bg-black/60 transition-opacity duration-150 motion-reduce:transition-none ${
                payload ? "opacity-100" : "opacity-0"
              }`}
              style={{ pointerEvents: "none" }}
            />
            <div
              ref={popRef}
              role="tooltip"
              aria-hidden={!payload}
              className={`fixed z-[70] max-w-[330px] rounded-xl border border-navy bg-surface px-3.5 py-3 text-[12.5px] leading-relaxed text-ink shadow-2xl transition-opacity duration-100 motion-reduce:transition-none ${
                payload && pos ? "opacity-100" : "opacity-0"
              }`}
              style={{
                pointerEvents: "none",
                left: pos ? pos.left : -9999,
                top: pos ? pos.top : -9999,
              }}
            >
              {payload && (
                <>
                  {payload.title && (
                    <div className="mb-1.5 flex items-center gap-2 font-semibold text-ink">
                      <span>{payload.title}</span>
                      {payload.tag ? <TagChip tag={payload.tag} /> : null}
                    </div>
                  )}
                  <div className="text-subtle">{payload.body}</div>
                </>
              )}
            </div>
          </>,
          document.body
        )}
    </ExplainCtx.Provider>
  );
}

// ExplainTrigger — wrap any label/element. Shows the overlay on hover AND focus (keyboard-
// reachable); hides on leave/blur. Captures its own rect at open time.
export function ExplainTrigger({
  title,
  tag,
  body,
  as: Tag = "span",
  className = "",
  style,
  children,
}) {
  const ctx = useContext(ExplainCtx);
  const ref = useRef(null);
  const open = () =>
    ctx?.show({ title, tag, body, rect: ref.current?.getBoundingClientRect() });
  const close = () => ctx?.hide();
  return (
    <Tag
      ref={ref}
      tabIndex={0}
      onMouseEnter={open}
      onMouseLeave={close}
      onFocus={open}
      onBlur={close}
      className={className}
      style={style}
    >
      {children}
    </Tag>
  );
}
