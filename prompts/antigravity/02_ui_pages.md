Branch: lane/ui-pages. Read /AGENTS.md and everything in /contracts first.

You are building the non-run pages of Fixie. You own ONLY frontend/app/page.tsx, frontend/app/eval,
frontend/components/home, frontend/components/eval, frontend/components/states. Do NOT edit frontend/lib or
frontend/components/run (another agent owns them); if you need their types, define small local ones. You may
add the `recharts` dependency to frontend/package.json (pinned exactly) and nothing else there. Follow every hard
rule in AGENTS.md (no keys, no live APIs, colours only from tokens.css, files under ~300 lines, no plan
documents, browser tool only in the final step).

BUILD
1. Home (/): a large one-line headline, one input (paste a GitHub issue URL), three example chips linking to
   showcase runs, a Live/Replay switch labelled exactly "Replay streams a real saved run", and showcase cards read
   from /replays/showcase.json. Exactly ONE subtle hero background effect (CSS + motion aurora or spotlight); no
   other decorative effects anywhere. Live is disabled, with a calm explanation, when NEXT_PUBLIC_API_URL is unset.
2. /eval: read /eval.json. A script frontend/scripts/copy-eval.mjs copies backend/eval/eval.json to
   frontend/public/eval.json (wire it to "predev" and "prebuild" by adding to the existing scripts without
   removing others, and tell me in your final message if that clashes with the other lane). Shape:
   { synthetic, provider, instances_total,
     baseline:{resolved,rounds,cost_usd,seconds,per_model}, branching:{same},
     results:[{id, baseline:{...}, branching:{...}}] }.
   Show ONE Recharts chart (resolve rate and cost per fix, baseline vs branching), a per-instance table, and a
   caveats box: models may have seen public benchmarks; the sample is small; which provider produced the numbers.
   When synthetic is true show a prominent amber banner: "Synthetic placeholder data, not a real result".
   Guard divide-by-zero: when resolved is 0 show "n/a" for cost per fix.
3. Shared states in components/states: skeletons, empty, error with retry, rate-limit (offers Replay),
   backend-asleep ("waking up", calm), 404.
4. A cmdk command palette (Ctrl/Cmd+K) to jump between showcase runs and pages. Export <CommandPalette/> from
   frontend/components/home; the one-line mount in layout.tsx belongs to the project owner, so say so in your
   final message.
5. Responsive down to 360px, keyboard accessible, metadata and favicon, dark theme only.

ACCEPTANCE (paste real output): `npm run lint` and `npm run build` pass. THEN, exactly once, screenshot / and
/eval at 1440px and 390px with the browser tool.
Final message: commits, unfinished items, and changes needed in files you do not own.
