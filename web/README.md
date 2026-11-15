# TRACE web

Next.js App Router frontend for the TRACE audit workflow. The current repo scaffold uses Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, and `@xyflow/react` (React Flow).

## Local development

```bash
cp .env.example .env.local
npm install
npm run dev
```

MSW starts in the browser by default when `NEXT_PUBLIC_API_URL` is unset. The mock handlers use clearly labelled synthetic data from `src/lib/mock-data.ts`. Set `NEXT_PUBLIC_API_URL` to a FastAPI origin to bypass MSW and call that service.

## API types

`src/lib/generated/api-schema.d.ts` is generated from `../docs/openapi.json`:

```bash
npm run api:types
```

That OpenAPI snapshot currently contains health, taxonomy, and demo-reset endpoints. Workflow UI endpoints outside the snapshot use the frozen TypeScript mirror in `src/lib/types.ts` and MSW demo handlers until the backend publishes them.

## Shared UI

Shared components are in `src/components` (`KpiTile`, `StatusBadge`, `DataTable`, `Timeline`, `EmptyState`, skeletons, and `useToast`). The shadcn-compatible component configuration is `components.json`; common Card primitives are in `src/components/ui/card.tsx`.
