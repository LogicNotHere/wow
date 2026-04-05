from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

dev_router = APIRouter()


PLAYGROUND_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WowShop Catalog Playground</title>
  <style>
    body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 20px; background: #f7f7f8; color: #111; }
    h1 { margin: 0 0 8px; }
    .muted { color: #555; margin-bottom: 16px; }
    .grid { display: grid; gap: 14px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .card { background: #fff; border: 1px solid #ddd; border-radius: 10px; padding: 14px; }
    .card h2 { font-size: 16px; margin: 0 0 12px; }
    label { display: block; margin: 8px 0 4px; font-size: 13px; color: #333; }
    input, textarea { width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #bbb; border-radius: 8px; font-size: 14px; }
    textarea { min-height: 80px; resize: vertical; }
    button { margin-top: 10px; background: #111; color: #fff; border: 0; border-radius: 8px; padding: 8px 12px; cursor: pointer; }
    button:hover { background: #000; }
    .wide { margin-bottom: 14px; }
    .result { margin-top: 14px; background: #0f172a; color: #e2e8f0; border-radius: 10px; padding: 10px; white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; min-height: 120px; }
  </style>
</head>
<body>
  <h1>Catalog Playground</h1>
  <div class="muted">Test create flow: Game -> Category -> Lot -> Page -> Block</div>

  <div class="card wide">
    <h2>Auth</h2>
    <label for="baseUrl">Base URL</label>
    <input id="baseUrl" value="/api/v1">
    <label for="bearer">Bearer Token (for admin/staff routes)</label>
    <input id="bearer" placeholder="Paste access token">
  </div>

  <div class="grid">
    <div class="card">
      <h2>Create Game (POST /admin/games)</h2>
      <label>Name</label><input id="gameName" value="World of Warcraft">
      <label>Slug</label><input id="gameSlug" value="world-of-warcraft">
      <label>Status (draft|active|inactive)</label><input id="gameStatus" value="draft">
      <label>Sort Order</label><input id="gameSort" value="0">
      <button onclick="createGame()">Create Game</button>
    </div>

    <div class="card">
      <h2>Create Category (POST /admin/categories)</h2>
      <label>Game ID</label><input id="catGameId" value="1">
      <label>Name</label><input id="catName" value="Mythic Plus">
      <label>Slug</label><input id="catSlug" value="mythic-plus">
      <label>Parent ID (optional)</label><input id="catParentId" value="">
      <label>Status (draft|active|inactive)</label><input id="catStatus" value="draft">
      <label>Sort Order</label><input id="catSort" value="0">
      <button onclick="createCategory()">Create Category</button>
    </div>

    <div class="card">
      <h2>Create Lot (POST /admin/lots)</h2>
      <label>Category ID</label><input id="lotCategoryId" value="1">
      <label>Name</label><input id="lotName" value="M+ 15 Boost">
      <label>Slug</label><input id="lotSlug" value="m-plus-15-boost">
      <label>Description</label><textarea id="lotDesc">Fast run with experienced booster</textarea>
      <label>Status (draft|active|inactive)</label><input id="lotStatus" value="active">
      <label>Base Price EUR</label><input id="lotPrice" value="25">
      <button onclick="createLot()">Create Lot</button>
    </div>

    <div class="card">
      <h2>Upsert Page (PUT /admin/lots/{lot_id}/page)</h2>
      <label>Lot ID</label><input id="pageLotId" value="1">
      <label>Title (optional)</label><input id="pageTitle" value="Mythic Plus 15 Boost">
      <label>Meta JSON (optional)</label><textarea id="pageMeta">{ "meta_title": "M+ 15", "meta_description": "Quick and safe run" }</textarea>
      <button onclick="upsertPage()">Upsert Page</button>
      <button onclick="getPage()">Get Page</button>
    </div>

    <div class="card">
      <h2>Create Block (POST /admin/lots/{lot_id}/page/blocks)</h2>
      <label>Lot ID</label><input id="blockLotId" value="1">
      <label>Type</label><input id="blockType" value="text">
      <label>Position (optional)</label><input id="blockPos" value="">
      <label>Payload JSON</label><textarea id="blockPayload">{ "text": "This is a test block" }</textarea>
      <button onclick="createBlock()">Create Block</button>
    </div>

    <div class="card">
      <h2>Patch/Delete Block</h2>
      <label>Lot ID</label><input id="editLotId" value="1">
      <label>Block ID</label><input id="editBlockId" value="1">
      <label>New Position (optional)</label><input id="editPos" value="">
      <label>Payload JSON (optional)</label><textarea id="editPayload">{ "text": "Updated block" }</textarea>
      <button onclick="patchBlock()">Patch Block</button>
      <button onclick="deleteBlock()">Delete Block</button>
    </div>
  </div>

  <pre id="result" class="result"></pre>

  <script>
    const result = document.getElementById("result");

    function toBool(v) {
      return String(v).trim().toLowerCase() === "true";
    }

    function toIntOrNull(v) {
      const s = String(v).trim();
      return s === "" ? null : Number.parseInt(s, 10);
    }

    function toFloat(v) {
      return Number.parseFloat(String(v).trim());
    }

    function parseJsonOrNull(text) {
      const raw = String(text).trim();
      if (raw === "") {
        return null;
      }
      return JSON.parse(raw);
    }

    async function callApi(path, method, payload) {
      const baseUrl = document.getElementById("baseUrl").value.trim().replace(/\\/$/, "");
      const token = document.getElementById("bearer").value.trim();
      const headers = { "Content-Type": "application/json" };
      if (token !== "") {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const opts = { method, headers };
      if (payload !== undefined) {
        opts.body = JSON.stringify(payload);
      }

      const res = await fetch(baseUrl + path, opts);
      const text = await res.text();
      let data = text;
      try {
        data = JSON.parse(text);
      } catch (_) {}
      result.textContent = `[${method}] ${baseUrl + path}\\nstatus: ${res.status}\\n\\n` + JSON.stringify(data, null, 2);
    }

    function createGame() {
      callApi("/admin/games/", "POST", {
        name: document.getElementById("gameName").value,
        slug: document.getElementById("gameSlug").value,
        status: String(document.getElementById("gameStatus").value).trim().toLowerCase(),
        sort_order: toIntOrNull(document.getElementById("gameSort").value) ?? 0
      });
    }

    function createCategory() {
      callApi("/admin/categories/", "POST", {
        game_id: toIntOrNull(document.getElementById("catGameId").value),
        name: document.getElementById("catName").value,
        slug: document.getElementById("catSlug").value,
        parent_id: toIntOrNull(document.getElementById("catParentId").value),
        status: String(document.getElementById("catStatus").value).trim().toLowerCase(),
        sort_order: toIntOrNull(document.getElementById("catSort").value) ?? 0
      });
    }

    function createLot() {
      callApi("/admin/lots/", "POST", {
        category_id: toIntOrNull(document.getElementById("lotCategoryId").value),
        name: document.getElementById("lotName").value,
        slug: document.getElementById("lotSlug").value,
        description: document.getElementById("lotDesc").value,
        status: String(document.getElementById("lotStatus").value).trim().toLowerCase(),
        base_price_eur: toFloat(document.getElementById("lotPrice").value)
      });
    }

    function upsertPage() {
      const lotId = toIntOrNull(document.getElementById("pageLotId").value);
      callApi(`/admin/lots/${lotId}/page`, "PUT", {
        title: document.getElementById("pageTitle").value.trim() || null,
        meta_json: parseJsonOrNull(document.getElementById("pageMeta").value)
      });
    }

    function getPage() {
      const lotId = toIntOrNull(document.getElementById("pageLotId").value);
      callApi(`/admin/lots/${lotId}/page`, "GET");
    }

    function createBlock() {
      const lotId = toIntOrNull(document.getElementById("blockLotId").value);
      callApi(`/admin/lots/${lotId}/page/blocks`, "POST", {
        type: document.getElementById("blockType").value,
        position: toIntOrNull(document.getElementById("blockPos").value),
        payload_json: parseJsonOrNull(document.getElementById("blockPayload").value)
      });
    }

    function patchBlock() {
      const lotId = toIntOrNull(document.getElementById("editLotId").value);
      const blockId = toIntOrNull(document.getElementById("editBlockId").value);
      callApi(`/admin/lots/${lotId}/page/blocks/${blockId}`, "PATCH", {
        position: toIntOrNull(document.getElementById("editPos").value),
        payload_json: parseJsonOrNull(document.getElementById("editPayload").value)
      });
    }

    function deleteBlock() {
      const lotId = toIntOrNull(document.getElementById("editLotId").value);
      const blockId = toIntOrNull(document.getElementById("editBlockId").value);
      callApi(`/admin/lots/${lotId}/page/blocks/${blockId}`, "DELETE");
    }
  </script>
</body>
</html>
"""


@dev_router.get(
    "/dev/catalog-playground",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def catalog_playground_page() -> HTMLResponse:
    return HTMLResponse(content=PLAYGROUND_HTML)
