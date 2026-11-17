// anxietyresult.js
// 文章は gettext() で翻訳される（翻訳は mentalhealth/locale/<言語>/LC_MESSAGES/djangojs.po）。

document.addEventListener("DOMContentLoaded", () => {
    const displayArea = document.getElementById('result-page-display');
    const soudanUrl = displayArea.dataset.soudanUrl;
    const takecareUrl = displayArea.dataset.takecareUrl;
    const homeUrl = displayArea.dataset.homeUrl;
    const anxietyUrl = displayArea.dataset.anxietyUrl;
    const aiUrl = displayArea.dataset.aiUrl;

    // URLからスコアを取得
    const urlParams = new URLSearchParams(window.location.search);
    const rawScore = urlParams.get('score');
    const score = parseInt(rawScore, 10);

    // GAD-7の有効範囲(0〜21)外、または未指定の場合はエラー表示
    if (rawScore === null || Number.isNaN(score) || score < 0 || score > 21) {
        displayArea.innerHTML = `
            <div class="result-content result-error">
                <span class="material-symbols-outlined result-icon">error</span>
                <p class="result-advice">${gettext("診断結果を表示できませんでした。もう一度チェックをやり直してください。")}</p>
                <div class="result-actions">
                    <a href="${anxietyUrl}" class="action-button small-button">${gettext("もう一度チェックする")}</a>
                </div>
            </div>
        `;
        return;
    }

    let resultText, adviceText, icon, resultClass;

    // GAD-7の公式スコア分類
    if (score <= 4) {
        resultText = gettext("不安は最小レベルです");
        adviceText = gettext("現在の状態は良好です。この調子で、日々のリフレッシュを大切にしましょう。");
        icon = "sentiment_very_satisfied";
        resultClass = "result-minimal";
    } else if (score <= 9) {
        resultText = gettext("軽度の不安");
        adviceText = gettext("軽度の不安を感じているようです。深呼吸や散歩など、簡単なリラクゼーションを試してみましょう。信頼できる人に話すのも良い方法です。");
        icon = "sentiment_satisfied";
        resultClass = "result-mild";
    } else if (score <= 14) {
        resultText = gettext("中等度の不安");
        adviceText = gettext("不安が日常生活に影響を与え始めているかもしれません。一人で抱え込まず、教員やカウンセラーへの相談を検討することをお勧めします。");
        icon = "sentiment_dissatisfied";
        resultClass = "result-moderate";
    } else {
        resultText = gettext("重度の不安");
        adviceText = gettext("専門的なサポートが必要なレベルの不安かもしれません。できるだけ早く、心療内科や精神科の専門医に相談してください。");
        icon = "sentiment_very_dissatisfied";
        resultClass = "result-severe";
    }

    const scoreText = interpolate(gettext("%(score)s点"), { score: score }, true);

    displayArea.innerHTML = `
        <div class="result-content ${resultClass}">
            <span class="material-symbols-outlined result-icon">${icon}</span>
            <p class="result-score">${gettext("合計スコア:")} <strong>${scoreText}</strong></p>
            <h3 class="result-diagnosis">${resultText}</h3>
            <p class="result-advice">${adviceText}</p>

            <div class="result-actions">
                <a href="${takecareUrl}" class="action-button small-button">${gettext("セルフケアのヒント")}</a>
                <a href="${soudanUrl}" class="action-button small-button">${gettext("教員・カウンセラーに相談")}</a>
                <a href="${aiUrl}" class="action-button small-button">${gettext("AIに相談")}</a>
            </div>
            <div class="result-actions">
                <a href="${homeUrl}" class="action-button small-button secondary">${gettext("ホームに戻る")}</a>
                <a href="${anxietyUrl}" class="action-button small-button secondary">${gettext("もう一度チェックする")}</a>
            </div>
        </div>
    `;
});
