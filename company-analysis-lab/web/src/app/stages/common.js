import { useEffect, useRef, useState } from "react";

/**
 * Local form state for a stage that autosaves (debounced) into doc.stages[n].answers.
 * `commit(extra)` writes the whole form immediately and merges `extra` into the stage state
 * (e.g. {submitted: {...}}), so submit handlers never race the debounce.
 */
export function useAnswers(app, n, path = null) {
  const read = () => {
    const a = app.doc.stages?.[n]?.answers || {};
    return path ? a[path] || {} : a;
  };
  const [form, setForm] = useState(read);
  const timer = useRef(null);
  const latest = useRef(form);

  const write = (values, extra) =>
    app.update((d) => {
      const s = (d.stages[n] ||= {});
      s.answers ||= {};
      if (path) s.answers[path] = { ...(s.answers[path] || {}), ...values };
      else s.answers = { ...s.answers, ...values };
      if (extra) extra(s);
    });

  const set = (k, v) => {
    const next = { ...latest.current, [k]: v };
    latest.current = next;
    setForm(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => write(latest.current), 400);
  };
  const commit = (extra) => {
    clearTimeout(timer.current);
    write(latest.current, extra);
  };
  useEffect(() => () => {
    if (timer.current) {
      clearTimeout(timer.current);
      write(latest.current);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return [form, set, commit];
}

export const st = (app, n) => app.doc.stages?.[n] || {};
export const answers = (app, n) => app.doc.stages?.[n]?.answers || {};
