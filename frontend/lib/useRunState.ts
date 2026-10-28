"use client";
import { useReducer, useEffect, useRef, useState } from "react";
import { createInitialState, foldEvent, type RunState } from "@/lib/events";
import { ReplaySource, LiveSource, type FixieSource, type EventSpeed } from "@/lib/source";

export function useRunState(runId: string) {
  const [state, dispatch] = useReducer(
    (s: RunState, ev: unknown) => foldEvent(s, ev),
    null,
    () => createInitialState(runId)
  );
  const [loading, setLoading] = useState(true);
  const [fatalError, setFatalError] = useState<string | null>(null);
  const sourceRef = useRef<FixieSource | null>(null);
  const [speed, setSpeedState] = useState<EventSpeed>(1);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    setLoading(true);
    setFatalError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "";
    const isInstant = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("instant") === "true";
    let src: FixieSource;

    if (apiUrl) {
      src = new LiveSource(runId, { apiUrl });
    } else {
      src = new ReplaySource(runId, { isInstant });
    }
    sourceRef.current = src;

    const unsub = src.subscribe(
      (ev) => {
        setLoading(false);
        dispatch(ev);
      },
      (err) => {
        // Fall back to replay on live error
        if (!(src instanceof ReplaySource)) {
          const replaySrc = new ReplaySource(runId);
          sourceRef.current = replaySrc;
          replaySrc.subscribe(
            (ev) => { setLoading(false); dispatch(ev); },
            (e2) => { setLoading(false); setFatalError(e2.message); },
            () => {}
          );
        } else {
          setLoading(false);
          setFatalError(err.message);
        }
      },
      () => setLoading(false)
    );

    return unsub;
  }, [runId]);

  function changeSpeed(s: EventSpeed) {
    sourceRef.current?.setSpeed(s);
    setSpeedState(s);
  }

  function togglePause() {
    if (paused) {
      sourceRef.current?.resume();
      setPaused(false);
    } else {
      sourceRef.current?.pause();
      setPaused(true);
    }
  }

  return { state, loading, fatalError, speed, paused, changeSpeed, togglePause };
}
