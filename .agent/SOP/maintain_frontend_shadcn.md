# SOP: Maintain the Shadcn/Tailwind Frontend

## Purpose
Describe the repeatable process for modifying the Vite + React frontend that relies on Tailwind CSS and shadcn/ui primitives. Follow this procedure when adding UI features, integrating new shadcn components, or adjusting styling tokens.

## Prerequisites
- Node 18+ with npm available locally.
- Repository dependencies installed (`npm install` inside `frontend/`).
- Familiarity with Tailwind utility classes, shadcn component patterns, and the project’s design tokens in `tailwind.config.js`.

## Steps
1. **Review Current Setup**  
   - Inspect `tailwind.config.js` for available theme tokens and component radius settings.  
   - Check `src/components/ui/` for existing shadcn primitives (Button, Card, Input, ScrollArea, etc.) before creating duplicates.  
   - Open `.agent/System/project_architecture.md` to understand layout expectations (transcript left, knowledge sidebar right).

2. **Plan the Change**  
   - Decide whether the update requires new shadcn components (`npx shadcn@latest add ...`) or adjustments to existing ones.  
   - For cross-cutting style updates, confirm the new tokens or variants you need (e.g., additional brand colors, radii).  
   - Sketch component hierarchies and data flow (props/state) before coding.

3. **Implement UI Updates**  
   - Create or update components under `src/components` using shadcn primitives from `src/components/ui`.  
   - Use Tailwind classes for layout (`grid`, `flex`, `gap-*`) and spacing; avoid bespoke CSS files unless absolutely necessary.  
   - Keep Spinner/Loader states consistent by reusing lucide icons (`Loader2`) inside shadcn buttons when waiting on async operations.  
   - For new primitives, run `npx shadcn@latest add <component>` (or copy the upstream recipe) and place the generated file in `src/components/ui`.

4. **Manage State & Accessibility**  
   - Store UI state in React hooks inside page-level components (e.g., `App.tsx`) and pass props down; keep shadcn primitives stateless.  
   - Ensure buttons and inputs expose accessible labels, `aria-live` regions, or roles when dynamic updates occur (e.g., microphone toggles, upload progress).  
   - Align conversation bubbles left/right based on speaker identity to keep the transcript legible.

5. **Tailwind & Config Changes**  
   - If you add design tokens, update `tailwind.config.js` (colors, animations) and restart the dev server to pick up new classes.  
   - Update `index.css` only for global resets or theme overrides (LiveKit modal styling, body gradients).

6. **Verify Build & UI**  
   - Re-run dependency installation if `package.json` changes (`npm install`), resolving any npm cache permission issues before proceeding.  
   - Execute `npm run build` to confirm Tailwind and TypeScript compile cleanly.  
   - Manually test key flows: joining a room, observing transcript alignment, using the knowledge upload button (spinner appears, list updates), and triggering LiveKit modals to ensure the dark backdrop displays correctly.

7. **Update Documentation**  
   - Reflect UI or workflow changes in `.agent/System/project_architecture.md` and `frontend/.env.example` when new env vars or features appear.  
   - Summarize the change (components touched, validations performed) in the PR description or handoff notes.

## Verification Checklist
- [ ] New/updated shadcn components live in `src/components/ui/`.  
- [ ] Tailwind classes compile (no `@apply` errors) and `npm run build` succeeds.  
- [ ] Transcript bubbles align left/right per speaker, and upload spinner appears during async work.  
- [ ] LiveKit modals show the themed translucent backdrop instead of a black square.  
- [ ] Documentation and env examples mention any new UI capabilities.

## Related Docs
- `.agent/System/project_architecture.md`
- `frontend/tailwind.config.js`
- `frontend/src/components/ui/*`
