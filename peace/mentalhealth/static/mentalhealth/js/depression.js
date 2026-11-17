// depression.js
// 文章は gettext() で翻訳される（翻訳は mentalhealth/locale/<言語>/LC_MESSAGES/djangojs.po）。

document.addEventListener("DOMContentLoaded", () => {
    const depressionTestForm = document.getElementById('depressionTestForm');
    const resultDisplay = document.getElementById('result');
    const checkerSection = document.getElementById('depression-checker-section');
    const soudanUrl = checkerSection.dataset.soudanUrl;
    const takecareUrl = checkerSection.dataset.takecareUrl;
    const aiUrl = checkerSection.dataset.aiUrl;
    const helpUrl = checkerSection.dataset.helpUrl;

    // フォームの送信イベントをリッスン
    depressionTestForm.addEventListener('submit', (e) => {
        e.preventDefault(); // フォームのデフォルト送信を防止
        calculateScore();
    });

    function calculateScore() {
        let score = 0;
        let allAnswered = true; // 全ての質問に回答したかチェック

        // 9問分のスコアを計算
        for (let i = 1; i <= 9; i++) {
            const radio = document.querySelector(`input[name="q${i}"]:checked`);
            if (radio) {
                score += parseInt(radio.value); // ラジオボタンの値をそのまま加算
            } else {
                allAnswered = false; // 未回答の質問があればフラグを立てる
            }
        }

        if (!allAnswered) {
            resultDisplay.innerHTML = `
                <div class="result-message error-message">
                    <span class="material-symbols-outlined">error</span>
                    <p>${gettext("すべての質問に回答してください。")}</p>
                </div>
            `;
            resultDisplay.style.display = 'block';
            return; // スコア計算を中断
        }

        let resultText = "";
        let adviceText = "";

        // PHQ-9の一般的なスコア解釈に基づいて調整
        if (score >= 0 && score <= 4) {
            resultText = gettext("うつ病の可能性は低いレベルです");
            adviceText = gettext("現在のうつ病の傾向は低めです。この状態を維持するために、日々のセルフケアを心がけ、心身の健康を保ちましょう。");
        } else if (score >= 5 && score <= 9) {
            resultText = gettext("軽度のうつ病の可能性");
            adviceText = gettext("軽度のうつ病の傾向が見られます。リラックスできる時間を意識的に作り、信頼できる人に相談してみましょう。セルフケアのヒントも参考にしてください。");
        } else if (score >= 10 && score <= 14) {
            resultText = gettext("中等度のうつ病の可能性");
            adviceText = gettext("中程度のうつ病の傾向が見られます。心の不調が続く場合は、教員やカウンセラー、または精神科・心療内科の専門医に相談することを検討してください。");
        } else if (score >= 15 && score <= 19) {
            resultText = gettext("中等度から重度のうつ病の可能性");
            adviceText = gettext("うつ病の傾向がかなり強く、専門的なサポートが推奨されます。一人で抱え込まず、精神科・心療内科の専門医に早めに相談し、適切な診断と治療を受けてください。");
        } else if (score >= 20 && score <= 27) { // 最大スコアは9問x3点=27点
            resultText = gettext("重度のうつ病の可能性");
            adviceText = gettext("非常に高いうつ病の傾向が見られ、緊急の専門的なサポートが必要です。すぐに精神科や心療内科を受診し、医師の診断と治療を受けてください。信頼できる大人に助けを求めることも重要です。");
        }

        // 質問9（死にたい・自分を傷つけたい気持ち）に少しでも当てはまる場合は、
        // 合計点に関係なく、すぐ話せる相談窓口を一番上に案内する
        const q9 = document.querySelector('input[name="q9"]:checked');
        const crisisNote = q9 && parseInt(q9.value) > 0 ? `
                <div class="crisis-note">
                    <p><strong>${gettext("つらい気持ちを教えてくれて、ありがとうございます。")}</strong></p>
                    <p>${gettext("「消えてしまいたい」と感じるほどつらいときは、ひとりで抱えないでください。")}
                    ${gettext("よりそいホットライン")} <a href="tel:0120279338">0120-279-338</a>（${gettext("24時間・無料")}）
                    ${gettext("など、今すぐ話を聞いてもらえる場所があります。")}</p>
                    <a href="${helpUrl}">${gettext("ほかの相談窓口を見る")}</a>
                </div>` : '';

        const scoreText = interpolate(gettext("%(score)s点"), { score: score }, true);

        resultDisplay.innerHTML = `
            <div class="result-content">
                <span class="material-symbols-outlined result-icon">favorite</span>
                <p class="result-score">${gettext("合計スコア:")} <strong>${scoreText}</strong></p>
                <h3 class="result-diagnosis">${resultText}</h3>
                ${crisisNote}
                <p class="result-advice">${adviceText}</p>
                <div class="result-actions">
                    <a href="${soudanUrl}" class="action-button small-button">${gettext("教員への相談")}</a>
                    <a href="${takecareUrl}" class="action-button small-button">${gettext("セルフケアのヒント")}</a>
                    <a href="${aiUrl}" class="action-button small-button">${gettext("AIに相談")}</a>
                </div>
                <p class="disclaimer">
                    ${gettext("※このチェックリストは簡易的なものであり、専門的な診断に代わるものではありません。")}<br>
                    ${gettext("心の不調が続く場合は、必ず専門医にご相談ください。")}
                </p>
            </div>
        `;
        resultDisplay.style.display = 'block';
        resultDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});
