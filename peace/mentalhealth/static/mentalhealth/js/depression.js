// depression.js

document.addEventListener("DOMContentLoaded", () => {
    const depressionTestForm = document.getElementById('depressionTestForm');
    const resultDisplay = document.getElementById('result');

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
                    <p>全ての質問に回答してください。</p>
                </div>
            `;
            resultDisplay.style.display = 'block';
            return; // スコア計算を中断
        }

        let resultText = "";
        let adviceText = "";
        let icon = ""; // 結果に応じたアイコン

        // PHQ-9の一般的なスコア解釈に基づいて調整
        if (score >= 0 && score <= 4) {
            resultText = "軽度のうつ病の可能性";
            adviceText = "現在のうつ病の傾向は低めです。この状態を維持するために、日々のセルフケアを心がけ、心身の健康を保ちましょう。";

        } else if (score >= 5 && score <= 9) {
            resultText = "軽度のうつ病の可能性";
            adviceText = "軽度のうつ病の傾向が見られます。リラックスできる時間を意識的に作り、信頼できる人に相談してみましょう。セルフケアのヒントも参考にしてください。";

        } else if (score >= 10 && score <= 14) {
            resultText = "中等度のうつ病の可能性";
            adviceText = "中程度のうつ病の傾向が見られます。心の不調が続く場合は、教員やカウンセラー、または精神科・心療内科の専門医に相談することを検討してください。";
            
        } else if (score >= 15 && score <= 19) {
            resultText = "中等度から重度のうつ病の可能性";
            adviceText = "うつ病の傾向がかなり強く、専門的なサポートが推奨されます。一人で抱え込まず、精神科・心療内科の専門医に早めに相談し、適切な診断と治療を受けてください。";
            
        } else if (score >= 20 && score <= 27) { // 最大スコアは9問x3点=27点
            resultText = "重度のうつ病の可能性";
            adviceText = "非常に高いうつ病の傾向が見られ、緊急の専門的なサポートが必要です。すぐに精神科や心療内科を受診し、医師の診断と治療を受けてください。信頼できる大人に助けを求めることも重要です。";
            
        }

        resultDisplay.innerHTML = `
            <div class="result-content">
                
                <p class="result-score">合計スコア: <strong>${score}点</strong></p>
                <h3 class="result-diagnosis">${resultText}</h3>
                <p class="result-advice">${adviceText}</p>
                <div class="result-actions">
                    <a href="{% url 'soudan_page' %}" class="action-button small-button">教員への相談</a>
                    <a href="{% url 'seishinka_page' %}" class="action-button small-button">精神科情報</a>
                    <a href="{% url 'takecare_page' %}" class="action-button small-button">セルフケアのヒント</a>
                </div>
                <p class="disclaimer">
                    ※このチェックリストは簡易的なものであり、専門的な診断に代わるものではありません。<br>
                    心の不調が続く場合は、必ず専門医にご相談ください。
                </p>
            </div>
        `;
        resultDisplay.style.display = 'block';
        // JSでの直接的な色指定はCSSに任せるため削除
    }
});
