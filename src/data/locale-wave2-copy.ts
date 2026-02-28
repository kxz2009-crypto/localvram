export const WAVE2_LOCALES = ["es", "pt", "fr", "de", "ru", "ja", "ko", "ar", "hi", "id", "zh"] as const;
export type Wave2Locale = (typeof WAVE2_LOCALES)[number];

type Wave2Copy = {
  guideTitle: string;
  guideDescription: string;
  guideHeading: string;
  guideIntro: string;
  modelTitle: string;
  modelDescription: string;
  modelHeading: string;
  modelIntro: string;
  ctaModel122: string;
  ctaModel35: string;
  ctaTool: string;
  ctaRuntimeGuide: string;
  ctaCostGuide: string;
};

export const LOCALE_WAVE2: Record<Wave2Locale, Wave2Copy> = {
  es: {
    guideTitle: "LocalVRAM ES | Ollama vs vLLM VRAM",
    guideDescription: "Comparacion practica de uso de VRAM y operacion entre Ollama y vLLM.",
    guideHeading: "Ollama vs vLLM: comparacion de VRAM y operacion",
    guideIntro: "Esta guia ayuda a decidir runtime, complejidad operativa y via de despliegue para cargas locales.",
    modelTitle: "LocalVRAM ES | Qwen3.5 122B Cloud",
    modelDescription: "Ruta recomendada para Qwen3.5 122B con enfoque cloud-first.",
    modelHeading: "Qwen3.5 122B: ruta cloud recomendada",
    modelIntro: "Qwen3.5 122B suele requerir estrategia cloud. Usa esta pagina para decidir costo y plan de fallback.",
    ctaModel122: "Abrir modelo 122B",
    ctaModel35: "Abrir modelo 35B",
    ctaTool: "Abrir calculadora VRAM",
    ctaRuntimeGuide: "Volver a guia de runtimes",
    ctaCostGuide: "Abrir guia de costo local vs cloud"
  },
  pt: {
    guideTitle: "LocalVRAM PT | Ollama vs vLLM VRAM",
    guideDescription: "Comparacao pratica de VRAM e operacao entre Ollama e vLLM.",
    guideHeading: "Ollama vs vLLM: comparacao de VRAM e operacao",
    guideIntro: "Este guia ajuda a decidir runtime, esforco operacional e estrategia de deploy para cargas locais.",
    modelTitle: "LocalVRAM PT | Qwen3.5 122B Cloud",
    modelDescription: "Rota recomendada para Qwen3.5 122B com estrategia cloud-first.",
    modelHeading: "Qwen3.5 122B: rota cloud recomendada",
    modelIntro: "Qwen3.5 122B normalmente exige estrategia em nuvem. Use esta pagina para decidir custo e fallback.",
    ctaModel122: "Abrir modelo 122B",
    ctaModel35: "Abrir modelo 35B",
    ctaTool: "Abrir calculadora de VRAM",
    ctaRuntimeGuide: "Voltar ao guia de runtimes",
    ctaCostGuide: "Abrir guia de custo local vs cloud"
  },
  fr: {
    guideTitle: "LocalVRAM FR | Ollama vs vLLM VRAM",
    guideDescription: "Comparaison pratique de la VRAM et de l'exploitation entre Ollama et vLLM.",
    guideHeading: "Ollama vs vLLM : comparaison VRAM et operations",
    guideIntro: "Ce guide aide a choisir le runtime, la complexite operationnelle et la voie de deploiement.",
    modelTitle: "LocalVRAM FR | Qwen3.5 122B Cloud",
    modelDescription: "Parcours recommande pour Qwen3.5 122B avec strategie cloud-first.",
    modelHeading: "Qwen3.5 122B : parcours cloud recommande",
    modelIntro: "Qwen3.5 122B demande souvent une approche cloud. Utilisez cette page pour cadrer cout et fallback.",
    ctaModel122: "Ouvrir le modele 122B",
    ctaModel35: "Ouvrir le modele 35B",
    ctaTool: "Ouvrir le calculateur VRAM",
    ctaRuntimeGuide: "Retour au guide runtime",
    ctaCostGuide: "Ouvrir le guide cout local vs cloud"
  },
  de: {
    guideTitle: "LocalVRAM DE | Ollama vs vLLM VRAM",
    guideDescription: "Praktischer Vergleich von VRAM-Nutzung und Betrieb zwischen Ollama und vLLM.",
    guideHeading: "Ollama vs vLLM: VRAM- und Betriebsvergleich",
    guideIntro: "Dieser Leitfaden hilft bei Runtime-Wahl, Betriebsaufwand und Deployment-Strategie.",
    modelTitle: "LocalVRAM DE | Qwen3.5 122B Cloud",
    modelDescription: "Empfohlener Cloud-Pfad fuer Qwen3.5 122B.",
    modelHeading: "Qwen3.5 122B: empfohlener Cloud-Pfad",
    modelIntro: "Qwen3.5 122B braucht meist eine Cloud-Strategie. Diese Seite unterstuetzt Kosten- und Fallback-Planung.",
    ctaModel122: "122B-Modell oeffnen",
    ctaModel35: "35B-Modell oeffnen",
    ctaTool: "VRAM-Rechner oeffnen",
    ctaRuntimeGuide: "Zurueck zum Runtime-Leitfaden",
    ctaCostGuide: "Leitfaden lokal vs cloud oeffnen"
  },
  ru: {
    guideTitle: "LocalVRAM RU | Ollama vs vLLM VRAM",
    guideDescription: "Практическое сравнение VRAM и эксплуатации Ollama и vLLM.",
    guideHeading: "Ollama vs vLLM: VRAM и эксплуатация",
    guideIntro: "Это руководство помогает выбрать рантайм, уровень сложности и стратегию развертывания.",
    modelTitle: "LocalVRAM RU | Qwen3.5 122B Cloud",
    modelDescription: "Рекомендуемый cloud-first путь для Qwen3.5 122B.",
    modelHeading: "Qwen3.5 122B: рекомендуемый cloud-путь",
    modelIntro: "Для Qwen3.5 122B обычно нужна облачная стратегия. Здесь фиксируется план по стоимости и fallback.",
    ctaModel122: "Открыть модель 122B",
    ctaModel35: "Открыть модель 35B",
    ctaTool: "Открыть VRAM-калькулятор",
    ctaRuntimeGuide: "Назад к гайду по рантаймам",
    ctaCostGuide: "Открыть гайд локально vs cloud"
  },
  ja: {
    guideTitle: "LocalVRAM JA | Ollama vs vLLM VRAM",
    guideDescription: "Ollama と vLLM の VRAM と運用を実務目線で比較。",
    guideHeading: "Ollama vs vLLM: VRAM と運用比較",
    guideIntro: "このガイドは、ランタイム選定・運用負荷・デプロイ方針の判断を支援します。",
    modelTitle: "LocalVRAM JA | Qwen3.5 122B Cloud",
    modelDescription: "Qwen3.5 122B 向け cloud-first 推奨ルート。",
    modelHeading: "Qwen3.5 122B: cloud 推奨ルート",
    modelIntro: "Qwen3.5 122B は多くの場合 cloud 前提です。このページでコストと fallback を整理します。",
    ctaModel122: "122B モデルを開く",
    ctaModel35: "35B モデルを開く",
    ctaTool: "VRAM 計算ツールを開く",
    ctaRuntimeGuide: "ランタイム比較ガイドに戻る",
    ctaCostGuide: "ローカル vs cloud コストガイドを開く"
  },
  ko: {
    guideTitle: "LocalVRAM KO | Ollama vs vLLM VRAM",
    guideDescription: "Ollama와 vLLM의 VRAM 사용과 운영 난이도를 실무 기준으로 비교합니다.",
    guideHeading: "Ollama vs vLLM: VRAM 및 운영 비교",
    guideIntro: "이 가이드는 런타임 선택, 운영 복잡도, 배포 전략 결정을 돕습니다.",
    modelTitle: "LocalVRAM KO | Qwen3.5 122B Cloud",
    modelDescription: "Qwen3.5 122B용 cloud-first 권장 경로.",
    modelHeading: "Qwen3.5 122B: cloud 권장 경로",
    modelIntro: "Qwen3.5 122B는 보통 클라우드 전략이 필요합니다. 이 페이지에서 비용과 fallback을 정리합니다.",
    ctaModel122: "122B 모델 열기",
    ctaModel35: "35B 모델 열기",
    ctaTool: "VRAM 계산기 열기",
    ctaRuntimeGuide: "런타임 비교 가이드로 돌아가기",
    ctaCostGuide: "로컬 vs 클라우드 비용 가이드 열기"
  },
  ar: {
    guideTitle: "LocalVRAM AR | Ollama vs vLLM VRAM",
    guideDescription: "مقارنة عملية بين Ollama و vLLM في استهلاك VRAM والتشغيل.",
    guideHeading: "Ollama vs vLLM: مقارنة VRAM والتشغيل",
    guideIntro: "يساعد هذا الدليل في اختيار بيئة التشغيل وتعقيد الإدارة ومسار النشر المناسب.",
    modelTitle: "LocalVRAM AR | Qwen3.5 122B Cloud",
    modelDescription: "مسار cloud-first موصى به لنموذج Qwen3.5 122B.",
    modelHeading: "Qwen3.5 122B: مسار سحابي موصى به",
    modelIntro: "غالبا ما يحتاج Qwen3.5 122B إلى استراتيجية سحابية. هذه الصفحة توضح التكلفة وخطة fallback.",
    ctaModel122: "فتح نموذج 122B",
    ctaModel35: "فتح نموذج 35B",
    ctaTool: "فتح أداة VRAM",
    ctaRuntimeGuide: "العودة إلى دليل المقارنة",
    ctaCostGuide: "فتح دليل التكلفة محلي vs سحابي"
  },
  hi: {
    guideTitle: "LocalVRAM HI | Ollama vs vLLM VRAM",
    guideDescription: "Ollama और vLLM के VRAM उपयोग और ऑपरेशन का व्यावहारिक तुलना गाइड।",
    guideHeading: "Ollama vs vLLM: VRAM और ऑपरेशन तुलना",
    guideIntro: "यह गाइड रनटाइम चयन, ऑपरेशनल जटिलता और डिप्लॉयमेंट रणनीति तय करने में मदद करता है।",
    modelTitle: "LocalVRAM HI | Qwen3.5 122B Cloud",
    modelDescription: "Qwen3.5 122B के लिए cloud-first अनुशंसित पथ।",
    modelHeading: "Qwen3.5 122B: अनुशंसित cloud पथ",
    modelIntro: "Qwen3.5 122B के लिए अक्सर क्लाउड रणनीति जरूरी होती है। इस पेज से लागत और fallback तय करें।",
    ctaModel122: "122B मॉडल खोलें",
    ctaModel35: "35B मॉडल खोलें",
    ctaTool: "VRAM कैलकुलेटर खोलें",
    ctaRuntimeGuide: "रनटाइम तुलना गाइड पर लौटें",
    ctaCostGuide: "लोकल vs क्लाउड लागत गाइड खोलें"
  },
  id: {
    guideTitle: "LocalVRAM ID | Ollama vs vLLM VRAM",
    guideDescription: "Perbandingan praktis penggunaan VRAM dan operasi antara Ollama dan vLLM.",
    guideHeading: "Ollama vs vLLM: perbandingan VRAM dan operasi",
    guideIntro: "Panduan ini membantu memilih runtime, kompleksitas operasional, dan strategi deployment.",
    modelTitle: "LocalVRAM ID | Qwen3.5 122B Cloud",
    modelDescription: "Rute cloud-first yang direkomendasikan untuk Qwen3.5 122B.",
    modelHeading: "Qwen3.5 122B: rute cloud yang direkomendasikan",
    modelIntro: "Qwen3.5 122B umumnya membutuhkan strategi cloud. Halaman ini membantu menyusun biaya dan fallback.",
    ctaModel122: "Buka model 122B",
    ctaModel35: "Buka model 35B",
    ctaTool: "Buka kalkulator VRAM",
    ctaRuntimeGuide: "Kembali ke panduan runtime",
    ctaCostGuide: "Buka panduan biaya lokal vs cloud"
  },
  zh: {
    guideTitle: "LocalVRAM 中文 | Ollama vs vLLM VRAM",
    guideDescription: "面向实操的 Ollama 与 vLLM 显存和运维对比。",
    guideHeading: "Ollama vs vLLM：显存与运维对比",
    guideIntro: "本页用于判断运行时选择、运维复杂度以及部署路径。",
    modelTitle: "LocalVRAM 中文 | Qwen3.5 122B Cloud",
    modelDescription: "Qwen3.5 122B 的 cloud-first 推荐路径。",
    modelHeading: "Qwen3.5 122B：云端优先路径",
    modelIntro: "Qwen3.5 122B 通常需要云端策略，本页用于快速判断成本与 fallback 方案。",
    ctaModel122: "打开 122B 模型页",
    ctaModel35: "打开 35B 模型页",
    ctaTool: "打开 VRAM 计算器",
    ctaRuntimeGuide: "返回运行时对比页",
    ctaCostGuide: "打开本地 vs 云成本页"
  }
};
