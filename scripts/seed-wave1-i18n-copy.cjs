#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const COPY_PATH = path.join(ROOT, "src", "data", "i18n-copy.json");

const TRANSLATIONS = {
  es: {
    "Back to Error KB": "Volver a la base de errores",
    "Back to Guides Hub": "Volver al centro de guias",
    "Back to Locale Home": "Volver al inicio del idioma",
    "Back to Models Hub": "Volver al centro de modelos",
    "Back to Status Hub": "Volver al centro de estado",
    "Back to Tools Hub": "Volver al centro de herramientas",
    "Current Rollout State": "Estado actual del despliegue",
    "English Source": "Fuente en ingles",
    "Error ID": "ID de error",
    "Error KB ({localeUpper})": "Base de errores ({localeUpper})",
    "Error routes are mirrored to preserve parity with English troubleshooting pages during i18n staging.":
      "Las rutas de errores se replican para mantener la paridad con las paginas de solucion de problemas en ingles durante la fase de i18n.",
    Group: "Grupo",
    "Group route parity is active. Group-level text is currently staged and will be localized after glossary QA.":
      "La paridad de rutas por grupo esta activa. El texto del grupo esta en fase y se localizara tras la QA del glosario.",
    Groups: "Grupos",
    Guide: "Guia",
    "Guide route parity is enabled. During rollout, page copy may temporarily fall back to English.":
      "La paridad de rutas de guias esta habilitada. Durante el despliegue, el contenido puede usar ingles temporalmente.",
    Guides: "Guias",
    "Guides Hub ({localeUpper})": "Centro de guias ({localeUpper})",
    "LocalVRAM ({localeUpper}) Error KB": "LocalVRAM ({localeUpper}) Base de errores",
    "LocalVRAM ({localeUpper}) Guides": "LocalVRAM ({localeUpper}) Guias",
    "LocalVRAM ({localeUpper}) Model Catalog": "LocalVRAM ({localeUpper}) Catalogo de modelos",
    "LocalVRAM ({localeUpper}) Status": "LocalVRAM ({localeUpper}) Estado",
    "LocalVRAM ({localeUpper}) Tools": "LocalVRAM ({localeUpper}) Herramientas",
    "LocalVRAM ({localeUpper}) | i18n Preview Hub": "LocalVRAM ({localeUpper}) | Centro de vista previa i18n",
    "LocalVRAM {localeUpper} route is active": "La ruta de LocalVRAM {localeUpper} esta activa",
    "Locale skeleton routes mapped 1:1 to English guide slugs.":
      "Rutas base de idioma mapeadas 1:1 con los slugs de guias en ingles.",
    "Localized Path": "Ruta localizada",
    "Localized error knowledge-base route skeleton aligned to English troubleshooting slugs.":
      "Estructura de ruta localizada de base de errores alineada con slugs de solucion en ingles.",
    "Localized guides route skeleton aligned to English guide slugs.":
      "Estructura de rutas de guias localizadas alineada con slugs en ingles.",
    "Localized model catalog route skeleton with slug parity to English model pages.":
      "Estructura de rutas del catalogo localizado con paridad de slugs respecto a las paginas en ingles.",
    "Localized route skeleton for home, guides, and status sections. Content fallback is temporarily English during i18n rollout.":
      "Estructura de rutas localizadas para inicio, guias y estado. El fallback de contenido usa ingles temporalmente durante el despliegue i18n.",
    "Localized route skeleton for model group '{groupName}'.":
      "Estructura de ruta localizada para el grupo de modelos '{groupName}'.",
    "Localized route skeleton for {modelName}. VRAM baseline: {minVram}GB min, {optimalVram}GB optimal.":
      "Estructura de ruta localizada para {modelName}. Linea base de VRAM: {minVram}GB minimo, {optimalVram}GB optimo.",
    "Localized status route skeleton for pipeline and operations visibility.":
      "Estructura de rutas de estado localizadas para visibilidad de pipeline y operaciones.",
    "Localized tool route skeletons aligned to English utility pages.":
      "Estructuras de rutas de herramientas localizadas alineadas con paginas utilitarias en ingles.",
    "Localized troubleshooting route is staged. Full locale copy will replace English fallback after QA.":
      "La ruta de solucion de problemas localizada esta en fase. El contenido completo del idioma reemplazara el fallback en ingles despues de QA.",
    "Minimum VRAM": "VRAM minima",
    Model: "Modelo",
    "Model Catalog ({localeUpper})": "Catalogo de modelos ({localeUpper})",
    "Model routes and group routes are staged for locale parity. Full translated model metadata is planned in later rollout.":
      "Las rutas de modelos y grupos estan en fase para paridad de idioma. La metadata traducida completa se planifica para un despliegue posterior.",
    Models: "Modelos",
    "Next Step": "Siguiente paso",
    "Open English Error KB": "Abrir base de errores en ingles",
    "Open English Guides": "Abrir guias en ingles",
    "Open English Model Catalog": "Abrir catalogo de modelos en ingles",
    "Open English Source": "Abrir fuente en ingles",
    "Open English Status": "Abrir estado en ingles",
    "Open English Tools": "Abrir herramientas en ingles",
    "Open Guides Hub": "Abrir centro de guias",
    "Open Model Catalog": "Abrir catalogo de modelos",
    "Open Status Hub": "Abrir centro de estado",
    "Open Submission Review": "Abrir revision de envios",
    "Open VRAM Calculator": "Abrir calculadora de VRAM",
    "Operational dashboards are available as localized route skeletons. Full locale content is staged per rollout plan.":
      "Los paneles operativos estan disponibles como rutas localizadas base. El contenido completo del idioma se habilitara segun el plan.",
    "Operational dashboards mirrored for locale path parity.":
      "Paneles operativos replicados para mantener paridad de rutas por idioma.",
    "Optimal VRAM": "VRAM optima",
    "Replace fallback content with locale-specific operations messaging and glossary-safe terms.":
      "Reemplazar contenido fallback con mensajes operativos especificos por idioma y terminos seguros del glosario.",
    "Replace fallback copy with fully localized content after glossary and terminology checks pass.":
      "Reemplazar el fallback con contenido totalmente localizado despues de aprobar glosario y terminologia.",
    Resource: "Recurso",
    "Route is active, canonical is locale-scoped, and hreflang is controlled by staged rollout policy.":
      "La ruta esta activa, el canonical esta acotado al idioma y hreflang esta controlado por la politica de despliegue por fases.",
    "Route parity and locale-level canonical paths are active for staged validation.":
      "La paridad de rutas y los canonicals por idioma estan activos para validacion por fases.",
    "Staged locale route for model detail parity. Full translated model profile is enabled after terminology and data QA.":
      "Ruta por idioma en fase para paridad de detalle de modelo. El perfil traducido completo se habilitara tras QA de terminologia y datos.",
    Status: "Estado",
    "Status Hub ({localeUpper})": "Centro de estado ({localeUpper})",
    "Status Page": "Pagina de estado",
    "This locale is in rollout mode. Navigation, route parity, and SEO tags are under staged validation.":
      "Este idioma esta en modo despliegue. Navegacion, paridad de rutas y etiquetas SEO estan en validacion por fases.",
    "This localized page is in staged rollout mode. Content quality gates and glossary checks are applied before index enablement.":
      "Esta pagina localizada esta en despliegue por fases. Se aplican controles de calidad y glosario antes de indexar.",
    "This status route is available for i18n parity validation. Full localized operational copy will be enabled after quality checks.":
      "Esta ruta de estado esta disponible para validar paridad i18n. El contenido operativo localizado completo se habilitara tras controles de calidad.",
    Tool: "Herramienta",
    "Tool routes are active for i18n parity. During staged rollout, utility page copy may temporarily use English fallback.":
      "Las rutas de herramientas estan activas para paridad i18n. Durante el despliegue por fases, pueden usar fallback en ingles temporalmente.",
    "Tools Hub ({localeUpper})": "Centro de herramientas ({localeUpper})",
    "Utility page route parity is enabled for i18n staging. Full localized instructions are enabled after terminology QA.":
      "La paridad de rutas de utilidades esta habilitada para la fase i18n. Las instrucciones localizadas completas se habilitan tras QA de terminologia.",
    "{errorId} ({localeUpper}) | LocalVRAM Error KB": "{errorId} ({localeUpper}) | LocalVRAM Base de errores",
    "{groupName} ({localeUpper}) | LocalVRAM Models": "{groupName} ({localeUpper}) | Modelos de LocalVRAM",
    "{itemDescription}": "{itemDescription}",
    "{itemTitle} ({localeUpper}) | LocalVRAM": "{itemTitle} ({localeUpper}) | LocalVRAM",
    "{modelName} ({localeUpper}) | LocalVRAM": "{modelName} ({localeUpper}) | LocalVRAM",
    "{symptom}": "{symptom}"
  },
  pt: {
    "Back to Error KB": "Voltar para a base de erros",
    "Back to Guides Hub": "Voltar para o hub de guias",
    "Back to Locale Home": "Voltar para a pagina inicial do idioma",
    "Back to Models Hub": "Voltar para o hub de modelos",
    "Back to Status Hub": "Voltar para o hub de status",
    "Back to Tools Hub": "Voltar para o hub de ferramentas",
    "Current Rollout State": "Estado atual do rollout",
    "English Source": "Fonte em ingles",
    "Error ID": "ID do erro",
    "Error KB ({localeUpper})": "Base de erros ({localeUpper})",
    "Error routes are mirrored to preserve parity with English troubleshooting pages during i18n staging.":
      "As rotas de erro sao espelhadas para manter paridade com as paginas de troubleshooting em ingles durante a fase de i18n.",
    Group: "Grupo",
    "Group route parity is active. Group-level text is currently staged and will be localized after glossary QA.":
      "A paridade de rotas de grupo esta ativa. O texto de nivel de grupo esta em fase e sera localizado apos QA de glossario.",
    Groups: "Grupos",
    Guide: "Guia",
    "Guide route parity is enabled. During rollout, page copy may temporarily fall back to English.":
      "A paridade de rotas de guias esta ativa. Durante o rollout, o texto pode usar fallback em ingles temporariamente.",
    Guides: "Guias",
    "Guides Hub ({localeUpper})": "Hub de guias ({localeUpper})",
    "LocalVRAM ({localeUpper}) Error KB": "LocalVRAM ({localeUpper}) Base de erros",
    "LocalVRAM ({localeUpper}) Guides": "LocalVRAM ({localeUpper}) Guias",
    "LocalVRAM ({localeUpper}) Model Catalog": "LocalVRAM ({localeUpper}) Catalogo de modelos",
    "LocalVRAM ({localeUpper}) Status": "LocalVRAM ({localeUpper}) Status",
    "LocalVRAM ({localeUpper}) Tools": "LocalVRAM ({localeUpper}) Ferramentas",
    "LocalVRAM ({localeUpper}) | i18n Preview Hub": "LocalVRAM ({localeUpper}) | Hub de preview i18n",
    "LocalVRAM {localeUpper} route is active": "A rota LocalVRAM {localeUpper} esta ativa",
    "Locale skeleton routes mapped 1:1 to English guide slugs.":
      "Rotas base de idioma mapeadas 1:1 para os slugs de guias em ingles.",
    "Localized Path": "Caminho localizado",
    "Localized error knowledge-base route skeleton aligned to English troubleshooting slugs.":
      "Estrutura de rota localizada da base de erros alinhada aos slugs em ingles.",
    "Localized guides route skeleton aligned to English guide slugs.":
      "Estrutura de rotas localizadas de guias alinhada aos slugs em ingles.",
    "Localized model catalog route skeleton with slug parity to English model pages.":
      "Estrutura de rotas do catalogo localizado com paridade de slug com paginas de modelos em ingles.",
    "Localized route skeleton for home, guides, and status sections. Content fallback is temporarily English during i18n rollout.":
      "Estrutura de rotas localizadas para home, guias e status. O fallback de conteudo usa ingles temporariamente durante o rollout de i18n.",
    "Localized route skeleton for model group '{groupName}'.":
      "Estrutura de rota localizada para o grupo de modelos '{groupName}'.",
    "Localized route skeleton for {modelName}. VRAM baseline: {minVram}GB min, {optimalVram}GB optimal.":
      "Estrutura de rota localizada para {modelName}. Base de VRAM: {minVram}GB minimo, {optimalVram}GB ideal.",
    "Localized status route skeleton for pipeline and operations visibility.":
      "Estrutura de rotas de status localizadas para visibilidade de pipeline e operacoes.",
    "Localized tool route skeletons aligned to English utility pages.":
      "Estruturas de rotas de ferramentas localizadas alinhadas as paginas utilitarias em ingles.",
    "Localized troubleshooting route is staged. Full locale copy will replace English fallback after QA.":
      "A rota localizada de troubleshooting esta em fase. O conteudo completo do idioma vai substituir o fallback em ingles apos QA.",
    "Minimum VRAM": "VRAM minima",
    Model: "Modelo",
    "Model Catalog ({localeUpper})": "Catalogo de modelos ({localeUpper})",
    "Model routes and group routes are staged for locale parity. Full translated model metadata is planned in later rollout.":
      "As rotas de modelos e de grupos estao em fase para paridade de idioma. A metadata traduzida completa esta planejada para etapa posterior.",
    Models: "Modelos",
    "Next Step": "Proximo passo",
    "Open English Error KB": "Abrir base de erros em ingles",
    "Open English Guides": "Abrir guias em ingles",
    "Open English Model Catalog": "Abrir catalogo de modelos em ingles",
    "Open English Source": "Abrir fonte em ingles",
    "Open English Status": "Abrir status em ingles",
    "Open English Tools": "Abrir ferramentas em ingles",
    "Open Guides Hub": "Abrir hub de guias",
    "Open Model Catalog": "Abrir catalogo de modelos",
    "Open Status Hub": "Abrir hub de status",
    "Open Submission Review": "Abrir revisao de submissao",
    "Open VRAM Calculator": "Abrir calculadora de VRAM",
    "Operational dashboards are available as localized route skeletons. Full locale content is staged per rollout plan.":
      "Dashboards operacionais estao disponiveis como rotas localizadas base. O conteudo completo por idioma sera liberado por fases.",
    "Operational dashboards mirrored for locale path parity.":
      "Dashboards operacionais espelhados para manter paridade de caminhos por idioma.",
    "Optimal VRAM": "VRAM ideal",
    "Replace fallback content with locale-specific operations messaging and glossary-safe terms.":
      "Substituir o conteudo fallback por mensagens operacionais especificas do idioma e termos seguros do glossario.",
    "Replace fallback copy with fully localized content after glossary and terminology checks pass.":
      "Substituir o fallback por conteudo totalmente localizado apos aprovacao do glossario e da terminologia.",
    Resource: "Recurso",
    "Route is active, canonical is locale-scoped, and hreflang is controlled by staged rollout policy.":
      "A rota esta ativa, o canonical esta no escopo do idioma e o hreflang e controlado pela politica de rollout por fases.",
    "Route parity and locale-level canonical paths are active for staged validation.":
      "A paridade de rotas e os canonicals por idioma estao ativos para validacao em fases.",
    "Staged locale route for model detail parity. Full translated model profile is enabled after terminology and data QA.":
      "Rota de idioma em fase para paridade de detalhes de modelo. O perfil traduzido completo sera ativado apos QA de terminologia e dados.",
    Status: "Status",
    "Status Hub ({localeUpper})": "Hub de status ({localeUpper})",
    "Status Page": "Pagina de status",
    "This locale is in rollout mode. Navigation, route parity, and SEO tags are under staged validation.":
      "Este idioma esta em modo de rollout. Navegacao, paridade de rotas e tags de SEO estao em validacao por fases.",
    "This localized page is in staged rollout mode. Content quality gates and glossary checks are applied before index enablement.":
      "Esta pagina localizada esta em modo de rollout por fases. Gates de qualidade e verificacoes de glossario sao aplicados antes da indexacao.",
    "This status route is available for i18n parity validation. Full localized operational copy will be enabled after quality checks.":
      "Esta rota de status esta disponivel para validacao de paridade i18n. O conteudo operacional localizado completo sera liberado apos as verificacoes.",
    Tool: "Ferramenta",
    "Tool routes are active for i18n parity. During staged rollout, utility page copy may temporarily use English fallback.":
      "As rotas de ferramentas estao ativas para paridade i18n. Durante o rollout em fases, o texto pode usar fallback em ingles temporariamente.",
    "Tools Hub ({localeUpper})": "Hub de ferramentas ({localeUpper})",
    "Utility page route parity is enabled for i18n staging. Full localized instructions are enabled after terminology QA.":
      "A paridade de rotas das paginas utilitarias esta ativa para a fase i18n. Instrucoes localizadas completas sao liberadas apos QA de terminologia.",
    "{errorId} ({localeUpper}) | LocalVRAM Error KB": "{errorId} ({localeUpper}) | LocalVRAM Base de erros",
    "{groupName} ({localeUpper}) | LocalVRAM Models": "{groupName} ({localeUpper}) | Modelos LocalVRAM",
    "{itemDescription}": "{itemDescription}",
    "{itemTitle} ({localeUpper}) | LocalVRAM": "{itemTitle} ({localeUpper}) | LocalVRAM",
    "{modelName} ({localeUpper}) | LocalVRAM": "{modelName} ({localeUpper}) | LocalVRAM",
    "{symptom}": "{symptom}"
  },
  ja: {
    "Back to Error KB": "エラーKBに戻る",
    "Back to Guides Hub": "ガイドハブに戻る",
    "Back to Locale Home": "言語ホームに戻る",
    "Back to Models Hub": "モデルハブに戻る",
    "Back to Status Hub": "ステータスハブに戻る",
    "Back to Tools Hub": "ツールハブに戻る",
    "Current Rollout State": "現在のロールアウト状態",
    "English Source": "英語ソース",
    "Error ID": "エラーID",
    "Error KB ({localeUpper})": "エラーKB ({localeUpper})",
    "Error routes are mirrored to preserve parity with English troubleshooting pages during i18n staging.":
      "i18n段階では、英語のトラブルシューティングページとの整合性を保つため、エラールートをミラーしています。",
    Group: "グループ",
    "Group route parity is active. Group-level text is currently staged and will be localized after glossary QA.":
      "グループルートのパリティは有効です。グループ説明は現在ステージ中で、用語集QA後にローカライズされます。",
    Groups: "グループ",
    Guide: "ガイド",
    "Guide route parity is enabled. During rollout, page copy may temporarily fall back to English.":
      "ガイドルートのパリティは有効です。ロールアウト中は一時的に英語フォールバックを使用する場合があります。",
    Guides: "ガイド",
    "Guides Hub ({localeUpper})": "ガイドハブ ({localeUpper})",
    "LocalVRAM ({localeUpper}) Error KB": "LocalVRAM ({localeUpper}) エラーKB",
    "LocalVRAM ({localeUpper}) Guides": "LocalVRAM ({localeUpper}) ガイド",
    "LocalVRAM ({localeUpper}) Model Catalog": "LocalVRAM ({localeUpper}) モデルカタログ",
    "LocalVRAM ({localeUpper}) Status": "LocalVRAM ({localeUpper}) ステータス",
    "LocalVRAM ({localeUpper}) Tools": "LocalVRAM ({localeUpper}) ツール",
    "LocalVRAM ({localeUpper}) | i18n Preview Hub": "LocalVRAM ({localeUpper}) | i18n プレビューハブ",
    "LocalVRAM {localeUpper} route is active": "LocalVRAM {localeUpper} ルートは有効です",
    "Locale skeleton routes mapped 1:1 to English guide slugs.":
      "ロケールのスケルトンルートは英語ガイドslugと1:1で対応しています。",
    "Localized Path": "ローカライズ済みパス",
    "Localized error knowledge-base route skeleton aligned to English troubleshooting slugs.":
      "英語トラブルシューティングslugに合わせた、ローカライズ済みエラーKBルートの骨格です。",
    "Localized guides route skeleton aligned to English guide slugs.":
      "英語ガイドslugに合わせたローカライズ済みガイドルートの骨格です。",
    "Localized model catalog route skeleton with slug parity to English model pages.":
      "英語モデルページとslugをそろえた、ローカライズ済みモデルカタログルートの骨格です。",
    "Localized route skeleton for home, guides, and status sections. Content fallback is temporarily English during i18n rollout.":
      "ホーム、ガイド、ステータス向けのローカライズ済みルート骨格です。i18nロールアウト中は一時的に英語フォールバックを使用します。",
    "Localized route skeleton for model group '{groupName}'.":
      "モデルグループ '{groupName}' 向けのローカライズ済みルート骨格です。",
    "Localized route skeleton for {modelName}. VRAM baseline: {minVram}GB min, {optimalVram}GB optimal.":
      "{modelName} 向けのローカライズ済みルート骨格です。VRAM基準: 最小 {minVram}GB、推奨 {optimalVram}GB。",
    "Localized status route skeleton for pipeline and operations visibility.":
      "パイプラインと運用可視化のためのローカライズ済みステータスルート骨格です。",
    "Localized tool route skeletons aligned to English utility pages.":
      "英語ユーティリティページに合わせたローカライズ済みツールルート骨格です。",
    "Localized troubleshooting route is staged. Full locale copy will replace English fallback after QA.":
      "ローカライズ済みトラブルシューティングルートはステージ中です。QA後に英語フォールバックを置き換えます。",
    "Minimum VRAM": "最小VRAM",
    Model: "モデル",
    "Model Catalog ({localeUpper})": "モデルカタログ ({localeUpper})",
    "Model routes and group routes are staged for locale parity. Full translated model metadata is planned in later rollout.":
      "モデルルートとグループルートはロケールパリティのためにステージ中です。完全な翻訳済みモデルメタデータは後続フェーズで対応します。",
    Models: "モデル",
    "Next Step": "次のステップ",
    "Open English Error KB": "英語のエラーKBを開く",
    "Open English Guides": "英語ガイドを開く",
    "Open English Model Catalog": "英語モデルカタログを開く",
    "Open English Source": "英語ソースを開く",
    "Open English Status": "英語ステータスを開く",
    "Open English Tools": "英語ツールを開く",
    "Open Guides Hub": "ガイドハブを開く",
    "Open Model Catalog": "モデルカタログを開く",
    "Open Status Hub": "ステータスハブを開く",
    "Open Submission Review": "投稿レビューを開く",
    "Open VRAM Calculator": "VRAM計算機を開く",
    "Operational dashboards are available as localized route skeletons. Full locale content is staged per rollout plan.":
      "運用ダッシュボードはローカライズ済みルート骨格として利用可能です。完全な言語コンテンツはロールアウト計画に沿って段階適用されます。",
    "Operational dashboards mirrored for locale path parity.":
      "ロケールのパス整合性を保つため、運用ダッシュボードをミラーしています。",
    "Optimal VRAM": "推奨VRAM",
    "Replace fallback content with locale-specific operations messaging and glossary-safe terms.":
      "フォールバック内容を、ロケール別の運用メッセージと用語集に準拠した用語に置き換えます。",
    "Replace fallback copy with fully localized content after glossary and terminology checks pass.":
      "用語集と用語チェック通過後、フォールバック文言を完全ローカライズ内容に置き換えます。",
    Resource: "リソース",
    "Route is active, canonical is locale-scoped, and hreflang is controlled by staged rollout policy.":
      "ルートは有効で、canonicalはロケールスコープ、hreflangは段階的ロールアウト方針で制御されています。",
    "Route parity and locale-level canonical paths are active for staged validation.":
      "段階的検証のため、ルートパリティとロケール単位のcanonicalパスが有効です。",
    "Staged locale route for model detail parity. Full translated model profile is enabled after terminology and data QA.":
      "モデル詳細パリティ用のロケールルートはステージ中です。用語とデータQA後に完全翻訳プロフィールを有効化します。",
    Status: "ステータス",
    "Status Hub ({localeUpper})": "ステータスハブ ({localeUpper})",
    "Status Page": "ステータスページ",
    "This locale is in rollout mode. Navigation, route parity, and SEO tags are under staged validation.":
      "このロケールはロールアウトモードです。ナビゲーション、ルートパリティ、SEOタグを段階的に検証しています。",
    "This localized page is in staged rollout mode. Content quality gates and glossary checks are applied before index enablement.":
      "このローカライズページは段階的ロールアウト中です。インデックス有効化前に品質ゲートと用語集チェックを適用します。",
    "This status route is available for i18n parity validation. Full localized operational copy will be enabled after quality checks.":
      "このステータスルートはi18nパリティ検証用です。品質チェック後に完全なローカライズ運用文言を有効化します。",
    Tool: "ツール",
    "Tool routes are active for i18n parity. During staged rollout, utility page copy may temporarily use English fallback.":
      "ツールルートはi18nパリティ向けに有効です。段階的ロールアウト中は一時的に英語フォールバックを利用する場合があります。",
    "Tools Hub ({localeUpper})": "ツールハブ ({localeUpper})",
    "Utility page route parity is enabled for i18n staging. Full localized instructions are enabled after terminology QA.":
      "ユーティリティページのルートパリティはi18nステージ向けに有効です。用語QA後に完全ローカライズ手順を有効化します。",
    "{errorId} ({localeUpper}) | LocalVRAM Error KB": "{errorId} ({localeUpper}) | LocalVRAM エラーKB",
    "{groupName} ({localeUpper}) | LocalVRAM Models": "{groupName} ({localeUpper}) | LocalVRAM モデル",
    "{itemDescription}": "{itemDescription}",
    "{itemTitle} ({localeUpper}) | LocalVRAM": "{itemTitle} ({localeUpper}) | LocalVRAM",
    "{modelName} ({localeUpper}) | LocalVRAM": "{modelName} ({localeUpper}) | LocalVRAM",
    "{symptom}": "{symptom}"
  }
};

function main() {
  const payload = JSON.parse(fs.readFileSync(COPY_PATH, "utf8"));
  const pages = payload.pages || {};
  const targetLocales = ["es", "pt", "ja"];

  for (const [pageId, page] of Object.entries(pages)) {
    const en = page.en || {};
    const locales = page.locales || {};
    for (const locale of targetLocales) {
      const catalog = TRANSLATIONS[locale];
      if (!catalog) {
        throw new Error(`missing translation catalog for ${locale}`);
      }
      const nextFields = {};
      for (const [field, enValue] of Object.entries(en)) {
        if (!(enValue in catalog)) {
          throw new Error(`missing '${locale}' translation for value: ${enValue}`);
        }
        nextFields[field] = catalog[enValue];
      }
      locales[locale] = nextFields;
    }
    page.locales = locales;
    pages[pageId] = page;
  }

  payload.pages = pages;
  fs.writeFileSync(COPY_PATH, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(`seeded locales: ${targetLocales.join(",")} for ${Object.keys(pages).length} pages`);
}

main();
