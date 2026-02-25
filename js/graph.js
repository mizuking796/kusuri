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
          'label': 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 4,
          'font-size': 9,
          'color': '#e4e6ed',
          'text-outline-color': '#0f1117',
          'text-outline-width': 1.5,
          'text-max-width': 90,
          'text-wrap': 'ellipsis',
          'min-zoomed-font-size': 8,
          'width': 24,
          'height': 24,
          'border-width': 1.5,
          'border-color': '#2d3348',
        }
      },
      // Base edge style
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'opacity': 0.6,
          'width': 1,
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
          'width': type === 'drug' ? 28 : type === 'category' ? 24 : 20,
          'height': type === 'drug' ? 28 : type === 'category' ? 24 : 20,
          'font-size': type === 'drug' ? 10 : 8,
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
        const w = cy.width();
        const h = cy.height();
        const scale = 0.55;
        options = {
          name: 'concentric',
          fit: true,
          padding: 20,
          boundingBox: {
            x1: w * (1 - scale) / 2,
            y1: h * (1 - scale) / 2,
            w: w * scale,
            h: h * scale,
          },
          concentric: node => node.degree(),
          levelWidth: () => 3,
          minNodeSpacing: 5,
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

  /** クラスターレイアウト（薬効分類別） */
  function applyClusterLayout() {
    const groups = KusuriData.CATEGORY_GROUPS;
    const catNodes = cy.nodes('[type="category"]');
    const drugNodes = cy.nodes('[type="drug"]');

    // Group center positions (circular arrangement)
    const groupNames = Object.keys(groups);
    const cx = cy.width() / 2;
    const cy_ = cy.height() / 2;
    const groupRadius = Math.min(cx, cy_) * 0.6;

    const groupPositions = {};
    groupNames.forEach((name, i) => {
      const angle = (2 * Math.PI * i) / groupNames.length - Math.PI / 2;
      groupPositions[name] = {
        x: cx + groupRadius * Math.cos(angle),
        y: cy_ + groupRadius * Math.sin(angle),
      };
    });

    // Assign each node to a group
    const nodePositions = {};

    // Category nodes: place at group center
    catNodes.forEach(node => {
      const code = node.data('code') || '';
      const prefix2 = code.substring(0, 2);
      let assignedGroup = 'その他';
      for (const [gName, prefixes] of Object.entries(groups)) {
        if (prefixes.includes(prefix2)) {
          assignedGroup = gName;
          break;
        }
      }
      const gPos = groupPositions[assignedGroup] || groupPositions['その他'];
      const jitter = (Math.random() - 0.5) * 80;
      nodePositions[node.id()] = { x: gPos.x + jitter, y: gPos.y + jitter };
    });

    // Drug nodes: place near their category
    drugNodes.forEach(node => {
      const tc = node.data('therapeutic_category') || '';
      const prefix2 = tc.substring(0, 2);
      let assignedGroup = 'その他';
      for (const [gName, prefixes] of Object.entries(groups)) {
        if (prefixes.includes(prefix2)) {
          assignedGroup = gName;
          break;
        }
      }
      const gPos = groupPositions[assignedGroup] || groupPositions['その他'];
      const angle = Math.random() * 2 * Math.PI;
      const r = 40 + Math.random() * 120;
      nodePositions[node.id()] = { x: gPos.x + r * Math.cos(angle), y: gPos.y + r * Math.sin(angle) };
    });

    // Other nodes (CYP, adverse effects): center area
    cy.nodes().forEach(node => {
      if (!nodePositions[node.id()]) {
        const type = node.data('type');
        if (type === 'cyp') {
          // CYP nodes: slightly offset from center
          const angle = Math.random() * 2 * Math.PI;
          const r = 30 + Math.random() * 60;
          nodePositions[node.id()] = { x: cx + r * Math.cos(angle), y: cy_ + r * Math.sin(angle) };
        } else {
          // Adverse effects: outer ring
          const angle = Math.random() * 2 * Math.PI;
          const r = groupRadius * 1.1 + Math.random() * 80;
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
  function applyFilters(filters) {
    if (!cy) return;

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
    const bb = cy.nodes().boundingBox();
    const w = cy.width();
    const h = cy.height();
    if (bb.w === 0 || bb.h === 0 || w === 0 || h === 0) return;

    // Manual viewport calculation (bypass cy.fit which may have issues)
    const padding = 60;
    const zoom = Math.min((w - padding * 2) / bb.w, (h - padding * 2) / bb.h);
    const cx = (bb.x1 + bb.x2) / 2;
    const cy_ = (bb.y1 + bb.y2) / 2;
    cy.viewport({
      zoom: zoom,
      pan: {
        x: w / 2 - zoom * cx,
        y: h / 2 - zoom * cy_,
      }
    });
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
