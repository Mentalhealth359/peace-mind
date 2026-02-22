// stress.js

document.addEventListener("DOMContentLoaded", () => {
    const stressTestForm = document.getElementById('stressTestForm');
    const resultDisplay = document.getElementById('result');

    // フォームの送信イベントをリッスン
    stressTestForm.addEventListener('submit', (e) => {
        e.preventDefault(); // フォームのデフォルト送信を防止
        calculateScore();
    });

    function calculateScore() {
        let score = 0;
        let allAnswered = true; // 全ての質問に回答したかチェック

        // 30問分のスコアを計算
        for (let i = 1; i <= 30; i++) { 
            const radio = document.querySelector(`input[name="q${i}"]:checked`);
            if (radio) {
                // value="1" の場合のみスコアを加算
                score += parseInt(radio.value); 
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

        // スコアに応じた診断結果とアドバイスを決定
        if (score >= 0 && score <= 5) {
            resultText = "正常です。これからもストレスと上手くつき合いましょう。";
            adviceText = "現在のストレスレベルは非常に低く、心身ともに良好な状態です。この調子を維持するために、日々のセルフケアを継続し、リラックスできる時間を持つことを心がけましょう。";
            icon = "sentiment_very_satisfied"; // とても幸せな顔
        } else if (score >= 6 && score <= 10) {
            resultText = "軽度ストレスです。ストレスがたまっているようなので休養が必要です。";
            adviceText = "軽度のストレスが蓄積している可能性があります。無理をせず、意識的に休息を取り、趣味やリラクゼーションで気分転換を図りましょう。教員や信頼できる友人への相談も有効です。";
            icon = "sentiment_satisfied"; // 幸せな顔
        } else if (score >= 11 && score <= 20) {
            resultText = "中等度ストレスです。ストレス状態が強いので医師へ相談することをお勧めします。";
            adviceText = "中程度のストレスが継続しているようです。心身の不調を感じる場合は、一人で抱え込まず、教員や専門のカウンセラー、心療内科などへの相談を強くお勧めします。適切なサポートで改善が見込めます。";
            icon = "sentiment_dissatisfied"; // 不満な顔
        } else if (score >= 21 && score <= 30) {
            resultText = "重度ストレスです。ひとりで悩まず心療内科や精神科を受診することをお勧めします。";
            adviceText = "非常に高いストレスレベルにあり、専門的なサポートが緊急に必要です。心身の健康を最優先し、すぐに精神科や心療内科を受診してください。家族や信頼できる大人に状況を伝え、助けを求めることも重要です。";
            icon = "sentiment_very_dissatisfied"; // とても悲しい顔
        }

        resultDisplay.innerHTML = `
            <div class="result-content">
                <span class="material-symbols-outlined result-icon">${icon}</span>
                <p class="result-score">あなたの採点は: <strong>${score}点</strong></p>
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
    }
});
