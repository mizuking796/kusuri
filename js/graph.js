/**
 * KusuriGraph — Cytoscape.js グラフ管理
 */
const KusuriGraph = (() => {

  let cy = null;

  /** Cytoscape.js 初期化 */
  function init(container) {
    cy = cytoscape({
      container,
      renderer: { name: 'canvas', webgl: true },
      minZoom: 0.05,
      maxZoom: 5,
      wheelSensitivity: 0.3,
      style: buildStyles(),
      layout: { name: 'preset' },
    });

    // Events
    cy.on('tap', 'node', e => {
      const node = e.target;
      selectNode(node);
      if (typeof KusuriApp !== 'undefined') {
        KusuriApp.showDetail(node.data());
      }
    });

    cy.on('tap', e => {
      if (e.target === cy) {
        deselectAll();
        if (typeof KusuriApp !== 'undefined') {
          KusuriApp.hideDetail();
        }
      }
    });

    return cy;
  }

  /** グラフスタイル定義 */
  function buildStyles() {
    const nodeTypes = KusuriData.NODE_TYPES;
    const edgeTypes = KusuriData.EDGE_TYPES;

    const styles = [
      // Base node style
      {
        selector: 'node',
        style: {
          'label': '',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 4,
          'font-size': 9,
          'color': '#e4e6ed',
          'text-outline-color': '#0f1117',
          'text-outline-width': 1.5,
          'text-max-width': 90,
          'text-wrap': 'ellipsis',
          'width': 4,
          'height': 4,
          'border-width': 0,
          'border-color': '#2d3348',
        }
      },
      // Base edge style
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'opacity': 0.15,
          'width': 0.5,
        }
      },
    ];

    // Node type styles
    for (const [type, cfg] of Object.entries(nodeTypes)) {
      styles.push({
        selector: `node[type="${type}"]`,
        style: {
          'background-color': cfg.color,
          'shape': cfg.shape,
          'width': type === 'drug' ? 4 : type === 'category' ? 'mapData(degree, 1, 50, 6, 25)' : 3,
          'height': type === 'drug' ? 4 : type === 'category' ? 'mapData(degree, 1, 50, 6, 25)' : 3,
          'font-size': type === 'drug' ? 10 : type === 'category' ? 11 : 8,
          'label': type === 'category' ? 'data(label)' : '',
          'text-opacity': type === 'category' ? 0.85 : 1,
        }
      });
    }

    // Edge type styles
    for (const [type, cfg] of Object.entries(edgeTypes)) {
      styles.push({
        selector: `edge[type="${type}"]`,
        style: {
          'line-color': cfg.color,
          'line-style': cfg.style,
          'width': cfg.width,
          'target-arrow-color': cfg.color,
          'target-arrow-shape': type === 'contraindication' ? 'tee' : 'triangle',
          'arrow-scale': 0.8,
        }
      });
    }

    // Selected / Highlighted states
    styles.push(
      {
        selector: 'node.highlighted',
        style: {
          'label': 'data(label)',
          'border-width': 3,
          'border-color': '#ffffff',
          'z-index': 999,
          'font-size': 14,
          'text-outline-width': 2,
        }
      },
      {
        selector: 'node.neighbor',
        style: {
          'label': 'data(label)',
          'opacity': 1,
          'border-width': 2,
          'border-color': '#5b8def',
        }
      },
      {
        selector: 'node.faded',
        style: { 'opacity': 0.12 }
      },
      {
        selector: 'edge.highlighted',
        style: { 'opacity': 1, 'z-index': 999 }
      },
      {
        selector: 'edge.faded',
        style: { 'opacity': 0.05 }
      },
      {
        selector: 'node.hidden',
        style: { 'display': 'none' }
      },
      {
        selector: 'edge.hidden',
        style: { 'display': 'none' }
      },
    );

    return styles;
  }

  /** グラフにデータをロード */
  function loadData(graphData) {
    if (!cy) return;

    const elements = [];

    // Nodes
    for (const node of graphData.nodes) {
      const label = node.name_ja || node.name_en || node.id;
      elements.push({
        group: 'nodes',
        data: {
          ...node,
          label,
          type: node.type,
        }
      });
    }

    // Edges
    for (const edge of graphData.edges) {
      elements.push({
        group: 'edges',
        data: {
          ...edge,
          source: edge.source,
          target: edge.target,
          type: edge.type,
        }
      });
    }

    cy.add(elements);
  }

  /** レイアウト適用 */
  function applyLayout(layoutName) {
    if (!cy) return;

    let options;

    switch (layoutName) {
      case 'concentric': {
        // 5リング preset レイアウト（等間隔）
        const radii = [0, 120, 240, 360, 480, 600];
        const rings = [[], [], [], [], [], []];
        cy.nodes().forEach(node => {
          const d = node.degree();
          let ring;
          if (d > 50) ring = 0;
          else if (d > 15) ring = 1;
          else if (d > 5) ring = 2;
          else if (d > 2) ring = 3;
          else if (d > 0) ring = 4;
          else ring = 5;
          rings[ring].push(node.id());
        });

        const positions = {};
        rings.forEach((ids, ringIdx) => {
          const r = radii[ringIdx];
          ids.forEach((id, i) => {
            const angle = (2 * Math.PI * i) / ids.length;
            positions[id] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
          });
        });

        options = {
          name: 'preset',
          positions: node => positions[node.id()] || { x: 0, y: 0 },
          fit: true,
          padding: 20,
          animate: false,
        };
        break;
      }

      case 'cluster':
        applyClusterLayout();
        return;

      case 'cose':
        options = {
          name: 'cose',
          idealEdgeLength: 80,
          nodeOverlap: 20,
          nodeRepulsion: 8000,
          edgeElasticity: 100,
          gravity: 0.25,
          numIter: 1000,
          animate: true,
          animationDuration: 800,
        };
        break;

      default:
        options = { name: 'concentric', concentric: n => n.degree(), levelWidth: () => 3 };
    }

    cy.layout(options).run();
  }

  /** クラスターレイアウト（薬効分類別・銀河風） */
  function applyClusterLayout() {
    const groups = KusuriData.CATEGORY_GROUPS;
    const catNodes = cy.nodes('[type="category"]');
    const drugNodes = cy.nodes('[type="drug"]');

    // グループの中心を大きな円上に配置
    const groupNames = Object.keys(groups);
    const cx = cy.width() / 2;
    const cy_ = cy.height() / 2;
    const groupRadius = Math.min(cx, cy_) * 3.5;

    // seed ベース乱数（毎回同じ配置）
    let _seed = 42;
    const srand = () => { _seed = (_seed * 9301 + 49297) % 233280; return _seed / 233280; };

    // ノードをグループに振り分け（先に集計してサイズ把握）
    const groupMembers = {};
    groupNames.forEach(n => { groupMembers[n] = []; });
    if (!groupMembers['その他']) groupMembers['その他'] = [];

    const assignGroup = (prefix2) => {
      for (const [gName, prefixes] of Object.entries(groups)) {
        if (prefixes.includes(prefix2)) return gName;
      }
      return 'その他';
    };

    catNodes.forEach(node => {
      const code = node.data('code') || '';
      const g = assignGroup(code.substring(0, 2));
      groupMembers[g].push(node.id());
    });

    drugNodes.forEach(node => {
      const tc = node.data('therapeutic_category') || '';
      const g = assignGroup(tc.substring(0, 2));
      groupMembers[g].push(node.id());
    });

    // グループサイズに応じた配置半径を計算
    const maxGroupSize = Math.max(...groupNames.map(n => (groupMembers[n] || []).length), 1);

    const groupPositions = {};
    groupNames.forEach((name, i) => {
      const angle = (2 * Math.PI * i) / groupNames.length - Math.PI / 2;
      groupPositions[name] = {
        x: cx + groupRadius * Math.cos(angle),
        y: cy_ + groupRadius * Math.sin(angle),
      };
    });

    // 各グループを小さな同心円（銀河風）に配置
    const nodePositions = {};
    for (const [gName, ids] of Object.entries(groupMembers)) {
      const gPos = groupPositions[gName] || { x: cx, y: cy_ };
      const count = ids.length;
      if (count === 0) continue;

      // グループサイズに応じてリング間隔を調整（大グループ=広い、小グループ=密）
      const sizeRatio = count / maxGroupSize;
      const ringSpacing = 80 + sizeRatio * 120;
      let placed = 0;
      let ringIdx = 0;

      while (placed < count) {
        const r = ringIdx * ringSpacing;
        const capacity = ringIdx === 0 ? 1 : Math.floor(2 * Math.PI * r / 8);
        const n = Math.min(capacity || 1, count - placed);
        for (let i = 0; i < n; i++) {
          const angle = (2 * Math.PI * i) / n + srand() * 0.15;
          const jitterR = r + (srand() - 0.5) * ringSpacing * 0.3;
          nodePositions[ids[placed]] = {
            x: gPos.x + Math.cos(angle) * jitterR,
            y: gPos.y + Math.sin(angle) * jitterR,
          };
          placed++;
        }
        ringIdx++;
      }
    }

    // CYP・副作用ノード: 中心付近
    cy.nodes().forEach(node => {
      if (!nodePositions[node.id()]) {
        const type = node.data('type');
        const angle = srand() * 2 * Math.PI;
        if (type === 'cyp') {
          const r = 20 + srand() * 50;
          nodePositions[node.id()] = { x: cx + r * Math.cos(angle), y: cy_ + r * Math.sin(angle) };
        } else {
          const r = groupRadius * 0.3 + srand() * groupRadius * 0.3;
          nodePositions[node.id()] = { x: cx + r * Math.cos(angle), y: cy_ + r * Math.sin(angle) };
        }
      }
    });

    cy.layout({
      name: 'preset',
      positions: node => nodePositions[node.id()] || { x: cx, y: cy_ },
      animate: true,
      animationDuration: 600,
      stop: () => cy.fit(undefined, 40),
    }).run();
  }

  /** ノード選択 → ハイライト */
  function selectNode(node) {
    deselectAll();

    node.addClass('highlighted');
    const neighborhood = node.neighborhood();
    neighborhood.nodes().addClass('neighbor');
    neighborhood.edges().addClass('highlighted');

    // Fade others
    cy.elements().not(node).not(neighborhood).addClass('faded');
  }

  /** 選択解除 */
  function deselectAll() {
    cy.elements().removeClass('highlighted neighbor faded');
  }

  /** ノードにフォーカス（ズーム + 選択） */
  function focusNode(nodeId) {
    const node = cy.getElementById(nodeId);
    if (!node || node.empty()) return;

    cy.animate({
      center: { eles: node },
      zoom: 2.5,
    }, {
      duration: 400,
      complete: () => {
        selectNode(node);
        if (typeof KusuriApp !== 'undefined') {
          KusuriApp.showDetail(node.data());
        }
      }
    });
  }

  /** フィルタ適用 */
  function applyFilters(filters, opts) {
    if (!cy) return;
    const hideOrphans = opts && opts.hideOrphans;

    // Node type filter
    for (const [type, visible] of Object.entries(filters.nodes)) {
      cy.nodes(`[type="${type}"]`)[visible ? 'removeClass' : 'addClass']('hidden');
    }

    // Edge type filter
    for (const [type, visible] of Object.entries(filters.edges)) {
      cy.edges(`[type="${type}"]`)[visible ? 'removeClass' : 'addClass']('hidden');
    }

    // Also hide edges connected to hidden nodes
    cy.edges().forEach(edge => {
      const src = edge.source();
      const tgt = edge.target();
      if (src.hasClass('hidden') || tgt.hasClass('hidden')) {
        edge.addClass('hidden');
      }
    });

    // Hide orphan nodes (no visible edges)
    if (hideOrphans) {
      cy.nodes().not('.hidden').forEach(node => {
        const visibleEdges = node.connectedEdges().not('.hidden');
        if (visibleEdges.length === 0) {
          node.addClass('hidden');
        }
      });
    }

    return getVisibleStats();
  }

  /** 表示中の統計 */
  function getVisibleStats() {
    const visibleNodes = cy.nodes().not('.hidden').length;
    const visibleEdges = cy.edges().not('.hidden').length;
    return { nodes: visibleNodes, edges: visibleEdges };
  }

  /** ズーム操作 */
  function zoomIn()  { cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width()/2, y: cy.height()/2 } }); }
  function zoomOut() { cy.zoom({ level: cy.zoom() / 1.3, renderedPosition: { x: cy.width()/2, y: cy.height()/2 } }); }
  function zoomFit() {
    cy.fit(cy.nodes().not('.hidden'), 40);
  }

  /** 全ノード取得 */
  function getNodes(type) {
    if (!cy) return [];
    const selector = type ? `node[type="${type}"]` : 'node';
    return cy.nodes(selector).map(n => n.data());
  }

  /** 特定ノードの接続情報取得 */
  function getConnections(nodeId) {
    if (!cy) return { edges: [], neighbors: [] };
    const node = cy.getElementById(nodeId);
    if (!node || node.empty()) return { edges: [], neighbors: [] };

    const edges = node.connectedEdges().map(e => e.data());
    const neighbors = node.neighborhood().nodes().map(n => n.data());
    return { edges, neighbors };
  }

  return {
    init,
    loadData,
    applyLayout,
    selectNode,
    deselectAll,
    focusNode,
    applyFilters,
    getVisibleStats,
    zoomIn,
    zoomOut,
    zoomFit,
    getNodes,
    getConnections,
    getCy: () => cy,
  };

})();
