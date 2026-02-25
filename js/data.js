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

  // 薬効分類マスタ（全カテゴリ）
  const THERAPEUTIC_CATEGORIES = {
    '11': '中枢神経系用薬',
    '12': '末梢神経系用薬',
    '13': '感覚器官用薬',
    '19': 'その他の神経系用薬',
    '21': '循環器官用薬',
    '22': '呼吸器官用薬',
    '23': '消化器官用薬',
    '24': 'ホルモン剤',
    '25': '泌尿生殖器官用薬',
    '26': '外皮用薬',
    '27': '歯科口腔用薬',
    '29': 'その他の個々の器官系用薬',
    '31': 'ビタミン剤',
    '32': '滋養強壮薬',
    '33': '血液・体液用薬',
    '39': '代謝性医薬品',
    '41': '細胞賦活用薬',
    '42': '腫瘍用薬',
    '43': '放射性医薬品',
    '44': 'アレルギー用薬',
    '49': 'その他の組織細胞機能用薬',
    '51': '漢方製剤',
    '52': '生薬',
    '61': '抗生物質',
    '62': '化学療法剤',
    '63': '生物学的製剤',
    '64': '寄生動物用薬',
    '71': '調剤用薬',
    '72': '診断用薬',
    '73': '公衆衛生用薬',
    '79': 'その他の治療を主目的としない薬',
    '81': '麻薬',
    '82': 'アルカロイド系麻薬',
  };

  // 主要カテゴリグループ（クラスター表示用）
  const CATEGORY_GROUPS = {
    '神経系': ['11', '12', '13', '19'],
    '循環器': ['21'],
    '消化器・呼吸器': ['22', '23'],
    'ホルモン・代謝': ['24', '25', '31', '32', '33', '39'],
    '漢方・生薬': ['51', '52'],
    '抗感染症': ['61', '62', '63', '64'],
    '免疫・腫瘍': ['41', '42', '43', '44', '49'],
    '外皮・歯科': ['26', '27', '29'],
    '診断・調剤': ['71', '72', '73', '79'],
    'その他': ['81', '82'],
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
