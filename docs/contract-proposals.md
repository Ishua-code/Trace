# Contract and schema proposals from Hanu (engine)

Nothing here changes `contracts.py` yet. Working versions are in `api/app/engine/`.
Please approve, change or reject each item.

## Blocking
1. **NCStore interface.** The engine reads data only through `engine/store.py::NCStore`
   (get NC, list NCs, actions, evidence, verifications, links, weight state). Please
   implement it on Postgres. `InMemoryStore` is the reference behaviour. Proposal: move the
   Protocol into `contracts.py` once agreed.
2. **`index_nc(nc_id) -> list[Link]`.** Please call it from NC create/update so links are
   stored. `find_related` then only reads. (Added to the engine class; not in the 4-method Protocol.)
3. **Tables** (Vercel has no writable disk):
   - `links(id pk, a text, b text, score float, signals jsonb, confirmed bool null, unique(a, b), check (a < b))`
   - `weight_deltas(name text pk, delta float)`
   - `weight_updates(id pk, link_id, confirmed, at, before jsonb, after jsonb)`
   `save_links(nc_id, links)` must replace all links touching `nc_id`, keeping the id and
   `confirmed` of any pair that already existed.
4. **Seed bundle.** `seed.generate.generate(seed)` returns contract objects (ncs, action_plans,
   evidence, verifications) plus `action_scope`; links will be precomputed so reset stays under
   10 seconds. Please write the loader that inserts the bundle. User ids in the seed are placeholders.

## Contract additions (additive)
5. `ActionPlan`: optional `applies_to_lines: list[str]` (and products) so rule R2 is honest.
   Until then the engine reads `store.get_action_scope_lines`.
6. New types `Graph`, `GraphNode`, `GraphEdge`, `FailurePath`, `WeightUpdate` (see `engine/types.py`),
   so Harish can mock the graph screen.
7. `Recommendation`: add `product` and `line` if the heatmap needs them.

## Agreements to confirm
8. **Unresolved** = any status except `CLOSED`.
9. Links are stored with `a < b`.
10. Tasks are generated once per closure report; later calls update the verdict only.
11. Canonical taxonomy lives in `engine/taxonomy.py`; department ids 1-7 and root-cause codes
    need your and Shamini's approval. Please expose it through a read-only endpoint.
12. `numpy`, `networkx`, `rapidfuzz` in `api/requirements.txt`; which Python version do CI and
    Vercel use (3.14 supported by Vercel)?