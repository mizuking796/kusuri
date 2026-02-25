/**
 * KusuriData — 定数・マスタ定義
 */
const KusuriData = (() => {

  // ノードタイプ定義
  const NODE_TYPES = {
    drug:           { label: '薬', shape: 'ellipse', color: '#5b8def' },
    category:       { label: '薬効分類', shape: 'round-rectangle', color: '#4ec9a0' },
    adverse_effect: { label: '副作用', shape: 'diamond', color: '#e06c75' },
    cyp:            { label: 'CYP酵素', shape: 'hexagon', color: '#c678dd' },
  };

  // エッジタイプ定義
  const EDGE_TYPES = {
    contraindication:     { label: '併用禁忌', color: '#e06c75', style: 'solid', width: 3 },
    precaution:           { label: '併用注意', color: '#e5c07b', style: 'dashed', width: 1.5 },
    causes_adverse_effect:{ label: '副作用', color: '#e06c75', style: 'dotted', width: 1 },
    belongs_to_category:  { label: '分類', color: '#4ec9a0', style: 'solid', width: 1 },
    metabolized_by:       { label: 'CYP代謝', color: '#c678dd', style: 'dashed', width: 1.5 },
  };

  // 薬効分類マスタ（主要カテゴリ）
  const THERAPEUTIC_CATEGORIES = {
    '11': '中枢神経系用薬',
    '12': '末梢神経系用薬',
    '13': '感覚器官用薬',
    '21': '循環器官用薬',
    '22': '呼吸器官用薬',
    '23': '消化器官用薬',
    '24': 'ホルモン剤',
    '25': '泌尿生殖器官用薬',
    '26': '外皮用薬',
    '31': 'ビタミン剤',
    '33': '血液・体液用薬',
    '39': '代謝性医薬品',
    '42': '腫瘍用薬',
    '44': 'アレルギー用薬',
    '61': '抗生物質',
    '62': '化学療法剤',
    '63': '生物学的製剤',
    '81': '麻薬',
  };

  // 主要カテゴリグループ（クラスター表示用）
  const CATEGORY_GROUPS = {
    '神経系': ['11', '12', '13'],
    '循環器': ['21'],
    '消化器・呼吸器': ['22', '23'],
    'ホルモン・代謝': ['24', '25', '31', '33', '39'],
    '抗感染症': ['61', '62', '63'],
    '免疫・腫瘍': ['42', '44'],
    'その他': ['26', '81'],
  };

  // 副作用の頻度ラベル
  const FREQUENCY_LABELS = {
    high:   { label: '高頻度', color: '#e06c75' },
    medium: { label: '中頻度', color: '#e5c07b' },
    low:    { label: '低頻度', color: '#98c379' },
    rare:   { label: 'まれ',   color: '#61afef' },
  };

  return {
    NODE_TYPES,
    EDGE_TYPES,
    THERAPEUTIC_CATEGORIES,
    CATEGORY_GROUPS,
    FREQUENCY_LABELS,
  };

})();
