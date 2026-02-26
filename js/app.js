/**
 * KusuriApp — アプリケーションコントローラ
 */
const KusuriApp = (() => {

  let graphData = null;
  let searchIndex = [];

  /** 初期化 */
  async function init() {
    setupGate();
  }

  // ===== Access Gate =====

  function setupGate() {
    const radios = document.querySelectorAll('input[name="gate-role"]');
    const enterBtn = document.getElementById('gate-enter');
    const warning = document.getElementById('gate-warning');

    // Check if already passed gate
    if (sessionStorage.getItem('kusuri_gate_passed') === '1') {
      passGate();
      return;
    }

    function updateGateBtn() {
      const val = document.querySelector('input[name="gate-role"]:checked')?.value;
      if (val === 'other') {
        enterBtn.disabled = true;
        warning.hidden = false;
      } else if (val) {
        enterBtn.disabled = false;
        warning.hidden = true;
      }
    }

    radios.forEach(r => r.addEventListener('change', updateGateBtn));

    // Handle browser-restored radio state
    updateGateBtn();

    enterBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const val = document.querySelector('input[name="gate-role"]:checked')?.value;
      if (val && val !== 'other') {
        sessionStorage.setItem('kusuri_gate_passed', '1');
        passGate();
      }
    });

  }

  function passGate() {
    document.getElementById('gate').hidden = true;
    document.getElementById('app').hidden = false;
    startApp();
  }

  // ===== App Start =====

  async function startApp() {
    const loadingText = document.getElementById('loading-text');
    const loadingBar = document.getElementById('loading-bar');

    function setProgress(pct, text) {
      if (loadingBar) loadingBar.style.width = pct + '%';
      if (loadingText) loadingText.textContent = text;
    }

    try {
      // Phase 1: Fetch data
      setProgress(10, 'データをダウンロード中...');
      const dataFile = window.__KUSURI_DATA || 'data/graph/graph-light.json';
      const res = await fetch(dataFile);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setProgress(30, 'データを解析中...');
      graphData = await res.json();

      // Phase 2: Init graph
      setProgress(40, 'グラフを初期化中...');
      await new Promise(r => setTimeout(r, 0)); // allow UI update
      KusuriGraph.init(document.getElementById('cy'));

      // Phase 3: Load data into graph
      setProgress(50, `${graphData.nodes.length} ノードを配置中...`);
      await new Promise(r => setTimeout(r, 0));
      KusuriGraph.loadData(graphData);

      // Phase 4: Build search index + UI
      setProgress(70, '検索インデックスを構築中...');
      await new Promise(r => setTimeout(r, 0));
      buildSearchIndex();
      setupSearch();
      setupFilters();
      setupLayout();
      setupQuickButtons();
      setupReverseLookup();
      setupRanking();
      setupZoomControls();
      setupSidebar();
      setupKeyboard();

      // Phase 5: Apply layout + fit
      setProgress(85, 'レイアウトを適用中...');
      await new Promise(r => setTimeout(r, 0));
      KusuriGraph.applyLayout('cluster');
      setProgress(95, '表示を調整中...');
      // Wait 500ms to ensure container is fully sized
      await new Promise(r => setTimeout(r, 500));
      KusuriGraph.zoomFit();
      // Done
      setProgress(100, '完了');
      updateStats();

      // Detail close button (register once)
      document.getElementById('detail-close').addEventListener('click', hideDetail);

      // Hide loading
      document.getElementById('loading').classList.add('hidden');

    } catch (err) {
      console.error('Failed to load data:', err);
      const errEl = document.getElementById('loading');
      errEl.textContent = '';
      const p1 = document.createElement('p');
      p1.style.color = 'var(--adverse_effect)';
      p1.textContent = 'データの読み込みに失敗しました';
      const p2 = document.createElement('p');
      p2.style.cssText = 'color: var(--text-dim); font-size: 13px; margin-top: 8px';
      p2.textContent = err.message;
      errEl.append(p1, p2);
    }
  }

  // ===== Search =====

  function buildSearchIndex() {
    searchIndex = [];
    for (const node of graphData.nodes) {
      const terms = [
        node.name_ja || '',
        node.name_en || '',
        node.search_name || '',
        ...(node.names_alt || []),
      ].filter(Boolean).map(t => t.toLowerCase());

      searchIndex.push({ id: node.id, type: node.type, name_ja: node.name_ja || '', name_en: node.name_en || '', terms });
    }
  }

  function setupSearch() {
    const input = document.getElementById('search-input');
    const results = document.getElementById('search-results');

    input.addEventListener('input', () => {
      const q = input.value.trim().toLowerCase();
      if (q.length < 1) {
        results.hidden = true;
        return;
      }

      const matches = searchIndex
        .filter(item => item.terms.some(t => t.includes(q)))
        .slice(0, 20);

      if (matches.length === 0) {
        results.innerHTML = '<div class="search-item"><span class="search-item-sub">該当なし</span></div>';
      } else {
        results.innerHTML = matches.map(m => {
          const typeCfg = KusuriData.NODE_TYPES[m.type] || {};
          return `<div class="search-item" data-id="${m.id}">
            <span class="node-badge ${m.type}" style="flex-shrink:0">${typeCfg.label || m.type}</span>
            <div>
              <div class="search-item-name">${escHtml(m.name_ja || m.name_en)}</div>
              ${m.name_en ? `<div class="search-item-sub">${escHtml(m.name_en)}</div>` : ''}
            </div>
          </div>`;
        }).join('');
      }

      results.hidden = false;
    });

    // Click on result
    results.addEventListener('click', e => {
      const item = e.target.closest('.search-item');
      if (!item) return;
      const id = item.dataset.id;
      if (id) {
        KusuriGraph.focusNode(id);
        input.value = '';
        results.hidden = true;
      }
    });

    // Close on outside click
    document.addEventListener('click', e => {
      if (!e.target.closest('.header-search')) {
        results.hidden = true;
      }
    });
  }

  // ===== Filters =====

  function setupFilters() {
    document.querySelectorAll('[data-filter]').forEach(cb => {
      cb.addEventListener('change', () => applyFilters());
    });
  }

  function applyFilters(opts) {
    const filters = { nodes: {}, edges: {} };

    document.querySelectorAll('[data-filter="node"]').forEach(cb => {
      filters.nodes[cb.dataset.type] = cb.checked;
    });
    document.querySelectorAll('[data-filter="edge"]').forEach(cb => {
      filters.edges[cb.dataset.type] = cb.checked;
    });

    KusuriGraph.applyFilters(filters, opts);
    updateStats();
  }

  // ===== Layout =====

  function setupLayout() {
    document.querySelectorAll('input[name="layout"]').forEach(r => {
      r.addEventListener('change', () => {
        KusuriGraph.applyLayout(r.value);
      });
    });
  }

  // ===== Quick Buttons =====

  function setupQuickButtons() {
    document.querySelectorAll('.quick-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const action = btn.dataset.quick;
        switch (action) {
          case 'ci-only':
            // Show only drugs with contraindication edges
            setAllCheckboxes('[data-filter="node"]', false);
            setAllCheckboxes('[data-filter="edge"]', false);
            document.querySelector('[data-filter="node"][data-type="drug"]').checked = true;
            document.querySelector('[data-filter="edge"][data-type="contraindication"]').checked = true;
            applyFilters({ hideOrphans: true });
            break;

          case 'drug-only':
            setAllCheckboxes('[data-filter="node"]', false);
            setAllCheckboxes('[data-filter="edge"]', false);
            document.querySelector('[data-filter="node"][data-type="drug"]').checked = true;
            document.querySelector('[data-filter="edge"][data-type="contraindication"]').checked = true;
            document.querySelector('[data-filter="edge"][data-type="precaution"]').checked = true;
            applyFilters({ hideOrphans: true });
            break;

          case 'reset':
            setAllCheckboxes('[data-filter]', true);
            applyFilters();
            break;
        }
      });
    });
  }

  function setAllCheckboxes(selector, checked) {
    document.querySelectorAll(selector).forEach(cb => {
      if (cb.type === 'checkbox') cb.checked = checked;
    });
  }

  // ===== Reverse Lookup =====

  let lookupType = '';
  let lookupSelected = new Set();

  function setupReverseLookup() {
    const modal = document.getElementById('lookup-modal');
    const closeBtn = document.getElementById('lookup-close');
    const filterInput = document.getElementById('lookup-filter');

    // Open buttons
    document.querySelectorAll('[data-lookup]').forEach(btn => {
      btn.addEventListener('click', () => {
        lookupType = btn.dataset.lookup;
        lookupSelected.clear();
        openLookupModal(lookupType);
      });
    });

    // Close
    closeBtn.addEventListener('click', () => { modal.hidden = true; });
    modal.addEventListener('click', e => {
      if (e.target === modal) modal.hidden = true;
    });

    // Filter input
    filterInput.addEventListener('input', () => {
      renderLookupTags(lookupType, filterInput.value.trim().toLowerCase());
    });
  }

  function openLookupModal(type) {
    const modal = document.getElementById('lookup-modal');
    const title = document.getElementById('lookup-title');
    const filterInput = document.getElementById('lookup-filter');

    const titles = {
      adverse_effect: '副作用 → 関連する薬を探す',
      cyp: 'CYP酵素 → 代謝される薬を探す',
      category: '薬効分類 → 所属する薬を探す',
    };
    title.textContent = titles[type] || '逆引き検索';
    filterInput.value = '';
    filterInput.placeholder = type === 'adverse_effect' ? '副作用名で絞り込み...'
      : type === 'cyp' ? 'CYP名で絞り込み...'
      : '分類名で絞り込み...';

    renderLookupTags(type, '');
    document.getElementById('lookup-results').innerHTML = '<p style="color:var(--text-dim);font-size:14px">上のタグを選択してください（複数選択可）</p>';
    modal.hidden = false;
    filterInput.focus();
  }

  function renderLookupTags(type, filter) {
    const container = document.getElementById('lookup-tags');
    const nodes = graphData.nodes.filter(n => n.type === type);

    // Sort by name
    nodes.sort((a, b) => {
      const na = a.name_ja || a.name_en || a.id;
      const nb = b.name_ja || b.name_en || b.id;
      return na.localeCompare(nb, 'ja');
    });

    const tagClass = type === 'adverse_effect' ? 'ae' : type === 'cyp' ? 'cyp' : 'cat';

    container.innerHTML = nodes
      .filter(n => {
        if (!filter) return true;
        const name = ((n.name_ja || '') + (n.name_en || '')).toLowerCase();
        return name.includes(filter);
      })
      .map(n => {
        const name = n.name_ja || n.name_en || n.id;
        const selected = lookupSelected.has(n.id) ? ' selected' : '';
        return `<span class="lookup-tag ${tagClass}${selected}" data-id="${n.id}">${escHtml(name)}</span>`;
      }).join('');

    // Tag click events
    container.querySelectorAll('.lookup-tag').forEach(tag => {
      tag.addEventListener('click', () => {
        const id = tag.dataset.id;
        if (lookupSelected.has(id)) {
          lookupSelected.delete(id);
          tag.classList.remove('selected');
        } else {
          lookupSelected.add(id);
          tag.classList.add('selected');
        }
        renderLookupResults(type);
      });
    });
  }

  function renderLookupResults(type) {
    const container = document.getElementById('lookup-results');

    if (lookupSelected.size === 0) {
      container.innerHTML = '<p style="color:var(--text-dim);font-size:14px">上のタグを選択してください（複数選択可）</p>';
      return;
    }

    // Find drugs connected to selected nodes
    const drugMap = new Map(); // drugId → { drug, matchedItems[] }

    for (const selectedId of lookupSelected) {
      const conn = KusuriGraph.getConnections(selectedId);
      const selectedNode = graphData.nodes.find(n => n.id === selectedId);
      const selectedName = selectedNode ? (selectedNode.name_ja || selectedNode.name_en) : selectedId;

      for (const neighbor of conn.neighbors) {
        if (neighbor.type === 'drug') {
          if (!drugMap.has(neighbor.id)) {
            drugMap.set(neighbor.id, { drug: neighbor, matchedItems: [] });
          }
          drugMap.get(neighbor.id).matchedItems.push(selectedName);
        }
      }
    }

    // Sort: drugs matching more selected items first
    const drugList = [...drugMap.values()].sort((a, b) => b.matchedItems.length - a.matchedItems.length);

    if (drugList.length === 0) {
      container.innerHTML = '<p style="color:var(--text-dim);font-size:14px">該当する薬が見つかりませんでした</p>';
      return;
    }

    // Group by match count if multiple selected
    let html = `<div class="lookup-results-header">${drugList.length}件の薬が見つかりました</div>`;

    if (lookupSelected.size > 1) {
      // Show drugs matching ALL selected first
      const allMatch = drugList.filter(d => d.matchedItems.length === lookupSelected.size);
      const partialMatch = drugList.filter(d => d.matchedItems.length < lookupSelected.size);

      if (allMatch.length > 0) {
        html += `<div class="lookup-result-group">
          <h4><span class="detail-tag ci" style="background:rgba(91,141,239,0.25);color:var(--accent)">全${lookupSelected.size}件に該当</span> ${allMatch.length}薬</h4>
          <div class="lookup-drug-list">
            ${allMatch.map(d => `<span class="lookup-drug" data-id="${d.drug.id}">${escHtml(d.drug.name_ja || d.drug.name_en || d.drug.id)}</span>`).join('')}
          </div>
        </div>`;
      }
      if (partialMatch.length > 0) {
        html += `<div class="lookup-result-group">
          <h4><span class="detail-tag" style="background:var(--surface2)">一部に該当</span> ${partialMatch.length}薬</h4>
          <div class="lookup-drug-list">
            ${partialMatch.map(d => `<span class="lookup-drug" data-id="${d.drug.id}" title="${d.matchedItems.join(', ')}">${escHtml(d.drug.name_ja || d.drug.name_en || d.drug.id)}</span>`).join('')}
          </div>
        </div>`;
      }
    } else {
      html += `<div class="lookup-result-group">
        <div class="lookup-drug-list">
          ${drugList.map(d => `<span class="lookup-drug" data-id="${d.drug.id}">${escHtml(d.drug.name_ja || d.drug.name_en || d.drug.id)}</span>`).join('')}
        </div>
      </div>`;
    }

    container.innerHTML = html;

    // Click to focus drug on graph
    container.querySelectorAll('.lookup-drug').forEach(el => {
      el.addEventListener('click', () => {
        document.getElementById('lookup-modal').hidden = true;
        KusuriGraph.focusNode(el.dataset.id);
      });
    });
  }

  // ===== Ranking =====

  const RANKING_TABS = [
    { id: 'ci',       label: '併用禁忌 TOP20',       badgeClass: 'ci' },
    { id: 'ddi',      label: '飲み合わせ注意 TOP20',  badgeClass: 'ci' },
    { id: 'ae',       label: '副作用が多い薬 TOP20',  badgeClass: 'ae' },
    { id: 'cyp',      label: 'CYP代謝が多い薬 TOP20', badgeClass: 'cyp' },
    { id: 'cyp-node', label: '関連薬が多いCYP酵素',   badgeClass: 'cyp' },
    { id: 'ae-node',  label: '関連薬が多い副作用',     badgeClass: 'ae' },
  ];

  let rankingCache = null;

  function setupRanking() {
    const modal = document.getElementById('ranking-modal');
    const closeBtn = document.getElementById('ranking-close');
    const openBtn = document.getElementById('ranking-btn');

    openBtn.addEventListener('click', () => {
      if (!rankingCache) rankingCache = computeRankings();
      renderRankingTabs('ci');
      modal.hidden = false;
    });

    closeBtn.addEventListener('click', () => { modal.hidden = true; });
    modal.addEventListener('click', e => {
      if (e.target === modal) modal.hidden = true;
    });
  }

  function computeRankings() {
    const cy = KusuriGraph.getCy();
    const drugNodes = cy.nodes('[type="drug"]');
    const cache = {};

    // Deduplicate by name: keep highest count per unique name
    function dedup(list) {
      const seen = new Map();
      for (const item of list) {
        const existing = seen.get(item.name);
        if (!existing || item.count > existing.count) {
          seen.set(item.name, item);
        }
      }
      return [...seen.values()].sort((a, b) => b.count - a.count);
    }

    // 1. 併用禁忌が多い薬 TOP20
    const ciList = [];
    drugNodes.forEach(node => {
      const count = node.connectedEdges('[type="contraindication"]').length;
      if (count > 0) ciList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count });
    });
    cache.ci = dedup(ciList).slice(0, 20);

    // 2. 飲み合わせ注意が多い薬 TOP20 (contraindication + precaution)
    const ddiList = [];
    drugNodes.forEach(node => {
      const count = node.connectedEdges('[type="contraindication"], [type="precaution"]').length;
      if (count > 0) ddiList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count });
    });
    cache.ddi = dedup(ddiList).slice(0, 20);

    // 3. 副作用が多い薬 TOP20
    const aeList = [];
    drugNodes.forEach(node => {
      const ae = node.data('adverse_effects') || [];
      if (ae.length > 0) aeList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count: ae.length });
    });
    cache.ae = dedup(aeList).slice(0, 20);

    // 4. CYP代謝が多い薬 TOP20
    const cypList = [];
    drugNodes.forEach(node => {
      const enzymes = node.data('cyp_enzymes') || [];
      if (enzymes.length > 0) cypList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count: enzymes.length });
    });
    cache.cyp = dedup(cypList).slice(0, 20);

    // 5. 関連薬が多いCYP酵素（全件）
    const cypNodes = cy.nodes('[type="cyp"]');
    const cypNodeList = [];
    cypNodes.forEach(node => {
      const drugCount = node.neighborhood().nodes('[type="drug"]').length;
      cypNodeList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count: drugCount });
    });
    cypNodeList.sort((a, b) => b.count - a.count);
    cache['cyp-node'] = cypNodeList;

    // 6. 関連薬が多い副作用（全件）
    const aeNodes = cy.nodes('[type="adverse_effect"]');
    const aeNodeList = [];
    aeNodes.forEach(node => {
      const drugCount = node.neighborhood().nodes('[type="drug"]').length;
      aeNodeList.push({ id: node.id(), name: node.data('name_ja') || node.data('name_en') || node.id(), count: drugCount });
    });
    aeNodeList.sort((a, b) => b.count - a.count);
    cache['ae-node'] = aeNodeList;

    return cache;
  }

  function renderRankingTabs(activeTabId) {
    const tabsContainer = document.getElementById('ranking-tabs');
    tabsContainer.innerHTML = RANKING_TABS.map(tab =>
      `<button class="ranking-tab${tab.id === activeTabId ? ' active' : ''}" data-tab="${tab.id}">${tab.label}</button>`
    ).join('');

    tabsContainer.querySelectorAll('.ranking-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        tabsContainer.querySelectorAll('.ranking-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        renderRankingList(btn.dataset.tab);
      });
    });

    renderRankingList(activeTabId);
  }

  function renderRankingList(tabId) {
    const container = document.getElementById('ranking-content');
    const data = rankingCache[tabId];
    const tabCfg = RANKING_TABS.find(t => t.id === tabId);
    const badgeClass = tabCfg ? tabCfg.badgeClass : '';

    if (!data || data.length === 0) {
      container.innerHTML = '<p style="color:var(--text-dim);font-size:14px">データがありません</p>';
      return;
    }

    const unitLabel = tabId === 'cyp-node' || tabId === 'ae-node' ? '薬' : '件';

    container.innerHTML = `<ul class="ranking-list">${data.map((item, i) => {
      const rank = i + 1;
      const rankClass = rank === 1 ? ' top1' : rank === 2 ? ' top2' : rank === 3 ? ' top3' : '';
      return `<li class="ranking-item" data-id="${item.id}">
        <span class="ranking-rank${rankClass}">${rank}</span>
        <span class="ranking-name">${escHtml(item.name)}</span>
        <span class="ranking-count ${badgeClass}">${item.count}${unitLabel}</span>
      </li>`;
    }).join('')}</ul>`;

    container.querySelectorAll('.ranking-item').forEach(el => {
      el.addEventListener('click', () => {
        document.getElementById('ranking-modal').hidden = true;
        KusuriGraph.focusNode(el.dataset.id);
      });
    });
  }

  // ===== Zoom Controls =====

  function setupZoomControls() {
    document.getElementById('zoom-in').addEventListener('click', KusuriGraph.zoomIn);
    document.getElementById('zoom-out').addEventListener('click', KusuriGraph.zoomOut);
    document.getElementById('zoom-fit').addEventListener('click', () => {
      KusuriGraph.deselectAll();
      hideDetail();
      KusuriGraph.zoomFit();
    });
  }

  // ===== Sidebar (Mobile) =====

  function setupSidebar() {
    const sidebar = document.getElementById('sidebar');
    const menuBtn = document.getElementById('menu-btn');
    const overlay = document.getElementById('sidebar-overlay');

    menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
    overlay.addEventListener('click', () => sidebar.classList.remove('open'));
  }

  // ===== Keyboard =====

  function setupKeyboard() {
    document.addEventListener('keydown', e => {
      if (e.key === '/' && !e.target.closest('input, textarea')) {
        e.preventDefault();
        document.getElementById('search-input').focus();
      }
      if (e.key === 'Escape') {
        hideDetail();
        KusuriGraph.deselectAll();
        document.getElementById('search-results').hidden = true;
        document.getElementById('lookup-modal').hidden = true;
        document.getElementById('ranking-modal').hidden = true;
        document.getElementById('sidebar').classList.remove('open');
      }
    });
  }

  // ===== Detail Panel =====

  function showDetail(nodeData) {
    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-content');

    const type = nodeData.type;
    let html = '';

    switch (type) {
      case 'drug':
        html = renderDrugDetail(nodeData);
        break;
      case 'category':
        html = renderCategoryDetail(nodeData);
        break;
      case 'adverse_effect':
        html = renderAdverseEffectDetail(nodeData);
        break;
      case 'cyp':
        html = renderCypDetail(nodeData);
        break;
      default:
        html = `<div class="detail-header"><div class="detail-name-ja">${escHtml(nodeData.label || nodeData.id)}</div></div>`;
    }

    content.innerHTML = html;
    content.scrollTop = 0;
    panel.hidden = false;

    // Link clicks
    content.querySelectorAll('.detail-link').forEach(link => {
      link.addEventListener('click', e => {
        e.preventDefault();
        const id = link.dataset.id;
        if (id) KusuriGraph.focusNode(id);
      });
    });

    // Translate buttons
    setupTranslateButtons();

  }

  function hideDetail() {
    document.getElementById('detail-panel').hidden = true;
  }

  /** 薬の詳細表示 */
  function renderDrugDetail(d) {
    const conn = KusuriGraph.getConnections(d.id);
    const edges = conn.edges;

    // DDI (contraindication + precaution)
    const ddiEdges = edges.filter(e => e.type === 'contraindication' || e.type === 'precaution');
    const ciEdges = ddiEdges.filter(e => e.type === 'contraindication' || e.severity === 'CI');
    const pEdges = ddiEdges.filter(e => e.type === 'precaution' && e.severity !== 'CI');

    // Get partner drug info for each DDI
    const ddiItems = ddiEdges.map(e => {
      const partnerId = e.source === d.id ? e.target : e.source;
      const partner = conn.neighbors.find(n => n.id === partnerId);
      return { ...e, partnerId, partnerName: partner?.name_ja || partner?.name_en || partnerId };
    }).sort((a, b) => {
      // CI first, then P
      if (a.severity === 'CI' && b.severity !== 'CI') return -1;
      if (a.severity !== 'CI' && b.severity === 'CI') return 1;
      return a.partnerName.localeCompare(b.partnerName);
    });

    // Adverse effects
    const aeList = (d.adverse_effects || []);

    // CYP
    const cypList = (d.cyp_enzymes || []);

    // Category
    const tc = d.therapeutic_category || '';
    const catEdge = edges.find(e => e.type === 'belongs_to_category');
    const catNode = catEdge ? conn.neighbors.find(n => n.type === 'category') : null;

    const hasJaName = !!(d.name_ja && d.name_ja !== d.name_en);
    let html = `
      <div class="detail-header">
        ${hasJaName
          ? `<div class="detail-name-ja">${escHtml(d.name_ja)}</div>
             <div class="detail-name-en">${escHtml(d.name_en || '')}</div>`
          : `<div class="detail-name-ja" id="detail-drug-name">${escHtml(d.name_en || '')}</div>
             <button class="translate-btn" data-translate-target="name" data-text="${escAttr(d.name_en || '')}">🌐 日本語名を取得</button>`}
        <span class="detail-type-badge" style="background:var(--drug-bg);color:var(--drug)">薬</span>
      </div>
    `;

    // Efficacy
    if (d.efficacy) {
      html += `
        <div class="detail-section">
          <h4>効能・効果</h4>
          <p class="efficacy-text">${escHtml(d.efficacy)}</p>
          <button class="translate-btn" data-translate-target="efficacy" data-text="${escAttr(d.efficacy)}">🌐 日本語に翻訳</button>
        </div>
      `;
    }

    // Category
    if (catNode) {
      html += `
        <div class="detail-section">
          <h4>薬効分類</h4>
          <p><a class="detail-link" data-id="${catNode.id}" href="#">${escHtml(catNode.name_ja || catNode.name_en)}</a></p>
        </div>
      `;
    }

    // CYP Enzymes
    if (cypList.length > 0) {
      html += `
        <div class="detail-section">
          <h4>代謝酵素（CYP）</h4>
          <p>${cypList.map(c => `<a class="detail-link detail-tag cyp" data-id="cyp_${c}" href="#">${c}</a>`).join(' ')}</p>
        </div>
      `;
    }

    // DDI
    if (ddiItems.length > 0) {
      html += `
        <div class="detail-section">
          <h4>飲み合わせ（${ciEdges.length > 0 ? `禁忌 ${ciEdges.length}件 / ` : ''}注意 ${pEdges.length}件）</h4>
          <div class="detail-ddi-list">
            ${ddiItems.map(item => `
              <div class="detail-ddi-item">
                <span class="detail-ddi-severity ${item.severity === 'CI' ? 'CI' : 'P'}">${item.severity === 'CI' ? '禁忌' : '注意'}</span>
                <a class="detail-link" data-id="${item.partnerId}" href="#">${escHtml(item.partnerName)}</a>
                ${item.mechanism && item.mechanism !== 'unclassified' ? `<span style="color:var(--text-dim);font-size:11px">${escHtml(item.mechanism)}</span>` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }

    // Adverse Effects
    if (aeList.length > 0) {
      html += `
        <div class="detail-section">
          <h4>副作用（${aeList.length}件）</h4>
          <ul>
            ${aeList.map(ae => {
              const freq = KusuriData.FREQUENCY_LABELS[ae.frequency] || {};
              return `<li>
                ${freq.label ? `<span class="detail-tag ae" style="color:${freq.color}">${freq.label}</span>` : ''}
                ${escHtml(ae.name)}
                ${ae.name_en ? `<span style="color:var(--text-dim);font-size:12px"> (${escHtml(ae.name_en)})</span>` : ''}
              </li>`;
            }).join('')}
          </ul>
        </div>
      `;
    }

    // Additional info
    if (d.atc_code) {
      html += `
        <div class="detail-section">
          <h4>その他情報</h4>
          <p style="font-size:13px;color:var(--text-dim)">
            DrugBank: ${escHtml(d.drugbank_id || d.id)}<br>
            ATC: ${escHtml(d.atc_code)}<br>
            ${d.formula ? `分子式: ${escHtml(d.formula)}` : ''}
          </p>
        </div>
      `;
    }

    return html;
  }

  /** 薬効分類の詳細 */
  function renderCategoryDetail(d) {
    const conn = KusuriGraph.getConnections(d.id);
    const drugs = conn.neighbors.filter(n => n.type === 'drug');

    let html = `
      <div class="detail-header">
        <div class="detail-name-ja">${escHtml(d.name_ja || '')}</div>
        <div class="detail-name-en">薬効分類コード: ${escHtml(d.code || '')}</div>
        <span class="detail-type-badge" style="background:var(--category-bg);color:var(--category)">薬効分類</span>
      </div>
      <div class="detail-section">
        <h4>この分類の薬（${drugs.length}件）</h4>
        <ul>
          ${drugs.map(drug => `<li><a class="detail-link" data-id="${drug.id}" href="#">${escHtml(drug.name_ja || drug.name_en || drug.id)}</a></li>`).join('')}
        </ul>
      </div>
    `;
    return html;
  }

  /** 副作用の詳細 */
  function renderAdverseEffectDetail(d) {
    const conn = KusuriGraph.getConnections(d.id);
    const drugs = conn.neighbors.filter(n => n.type === 'drug');

    let html = `
      <div class="detail-header">
        <div class="detail-name-ja">${escHtml(d.name_ja || '')}</div>
        <div class="detail-name-en">${escHtml(d.name_en || '')}</div>
        <span class="detail-type-badge" style="background:var(--adverse_effect-bg);color:var(--adverse_effect)">副作用</span>
      </div>
      <div class="detail-section">
        <h4>関連する薬（${drugs.length}件）</h4>
        <ul>
          ${drugs.map(drug => `<li><a class="detail-link" data-id="${drug.id}" href="#">${escHtml(drug.name_ja || drug.name_en || drug.id)}</a></li>`).join('')}
        </ul>
      </div>
    `;
    return html;
  }

  /** CYP酵素の詳細 */
  function renderCypDetail(d) {
    const conn = KusuriGraph.getConnections(d.id);
    const drugs = conn.neighbors.filter(n => n.type === 'drug');

    let html = `
      <div class="detail-header">
        <div class="detail-name-ja">${escHtml(d.name_ja || d.name_en || '')}</div>
        <span class="detail-type-badge" style="background:var(--cyp-bg);color:var(--cyp)">CYP酵素</span>
      </div>
      <div class="detail-section">
        <h4>この酵素で代謝される薬（${drugs.length}件）</h4>
        <p style="font-size:13px;color:var(--text-dim);margin-bottom:8px">
          同じCYP酵素で代謝される薬同士は、飲み合わせで血中濃度が変動するリスクがあります。
        </p>
        <ul>
          ${drugs.map(drug => `<li><a class="detail-link" data-id="${drug.id}" href="#">${escHtml(drug.name_ja || drug.name_en || drug.id)}</a></li>`).join('')}
        </ul>
      </div>
    `;
    return html;
  }

  // ===== Stats =====

  function updateStats() {
    const stats = KusuriGraph.getVisibleStats();
    document.getElementById('stat-nodes').textContent = stats.nodes;
    document.getElementById('stat-edges').textContent = stats.edges;
  }

  // ===== Translation =====

  const translationCache = {};

  async function translateText(text) {
    if (translationCache[text]) return translationCache[text];

    try {
      const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(text)}&langpair=en|ja`;
      const res = await fetch(url);
      const data = await res.json();
      const translated = data.responseData?.translatedText;
      if (translated && translated !== text) {
        translationCache[text] = translated;
        return translated;
      }
      return null;
    } catch {
      return null;
    }
  }

  function setupTranslateButtons() {
    document.getElementById('detail-content').querySelectorAll('.translate-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const text = btn.dataset.text;
        const target = btn.dataset.translateTarget;
        btn.textContent = '翻訳中...';
        btn.disabled = true;

        const result = await translateText(text);
        if (result) {
          if (target === 'name') {
            const nameEl = document.getElementById('detail-drug-name');
            if (nameEl) {
              // Show Japanese name as main, English as sub
              nameEl.textContent = result;
              const enSub = document.createElement('div');
              enSub.className = 'detail-name-en';
              enSub.textContent = text;
              nameEl.after(enSub);
            }
          } else if (target === 'efficacy') {
            const p = btn.previousElementSibling;
            if (p) p.textContent = result;
          }
          btn.textContent = '✓ 翻訳済み';
        } else {
          btn.textContent = '翻訳失敗（再試行）';
          btn.disabled = false;
        }
      });
    });
  }

  // ===== Utility =====

  function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
  }

  function escAttr(str) {
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  return { init, showDetail, hideDetail };

})();

// Boot
document.addEventListener('DOMContentLoaded', () => KusuriApp.init());
