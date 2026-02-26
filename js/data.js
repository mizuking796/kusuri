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

  // 薬効分類マスタ（全カテゴリ）— 日本標準商品分類番号 87類に準拠
  const THERAPEUTIC_CATEGORIES = {
    '11': '中枢神経系用薬',
    '12': '末梢神経系用薬',
    '13': '感覚器官用薬',
    '19': 'その他の神経系及び感覚器官用医薬品',
    '21': '循環器官用薬',
    '22': '呼吸器官用薬',
    '23': '消化器官用薬',
    '24': 'ホルモン剤（抗ホルモン剤を含む）',
    '25': '泌尿生殖器官及び肛門用薬',
    '26': '外皮用薬',
    '27': '歯科口腔用薬',
    '29': 'その他の個々の器官系用医薬品',
    '31': 'ビタミン剤',
    '32': '滋養強壮薬',
    '33': '血液・体液用薬',
    '34': '人工透析用薬',
    '39': 'その他の代謝性医薬品',
    '41': '細胞賦活用薬',
    '42': '腫瘍用薬',
    '43': '放射性医薬品',
    '44': 'アレルギー用薬',
    '49': 'その他の組織細胞機能用医薬品',
    '51': '生薬',
    '52': '漢方製剤',
    '59': 'その他の生薬及び漢方処方に基づく医薬品',
    '61': '抗生物質製剤',
    '62': '化学療法剤',
    '63': '生物学的製剤',
    '64': '寄生動物用薬',
    '71': '調剤用薬',
    '72': '診断用薬',
    '73': '公衆衛生用薬',
    '79': 'その他の治療を主目的としない医薬品',
    '81': 'アルカロイド系麻薬',
    '82': '非アルカロイド系麻薬',
  };

  // 主要カテゴリグループ（クラスター表示用・20分類）
  const CATEGORY_GROUPS = {
    '中枢神経':       ['11'],
    '末梢神経':       ['12'],
    '感覚器':        ['13', '19'],
    '循環器':        ['21'],
    '呼吸器':        ['22'],
    '消化器':        ['23'],
    'ホルモン':       ['24'],
    '泌尿・生殖':     ['25'],
    '外皮':         ['26', '27', '29'],
    'ビタミン・栄養':   ['31', '32'],
    '血液':         ['33', '34'],
    '代謝':         ['39'],
    '腫瘍':         ['42', '43'],
    '免疫・アレルギー':  ['41', '44', '49'],
    '漢方・生薬':     ['51', '52', '59'],
    '抗生物質':       ['61'],
    '化学療法':       ['62'],
    '生物学的製剤':    ['63', '64'],
    '診断・調剤':     ['71', '72', '73', '79'],
    '麻薬':         ['81', '82'],
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
