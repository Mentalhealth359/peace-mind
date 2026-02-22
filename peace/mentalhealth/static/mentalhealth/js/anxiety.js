document.addEventListener("DOMContentLoaded", () => {
    const gad7Form = document.getElementById('gad7Form');
    const resultDisplay = document.getElementById('result-display-area');
    const questionBlocks = document.querySelectorAll('.question-block');

    // --- ここが重要 ---
    // HTMLのdata-*属性からURLを取得する
    const checkerSection = document.getElementById('anxiety-checker-section');
    const soudanUrl = checkerSection.dataset.soudanUrl;
    const seishinkaUrl = checkerSection.dataset.seishinkaUrl;
    const takecareUrl = checkerSection.dataset.takecareUrl;
    const homeUrl = checkerSection.dataset.homeUrl;
    // --- ここまで ---

    // フォーム送信時の処理
    gad7Form.addEventListener('submit', (e) => {
        e.preventDefault();
        calculateGAD7Score();
        resultDisplay.scrollIntoView({ behavior: 'smooth' }); // 結果表示エリアへスクロール
    });
    
    // 各質問ブロックにクリックイベントを追加して自動スクロール
    questionBlocks.forEach((currentBlock, index) => {
        const radios = currentBlock.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', () => {
                // 最後の質問でなければ、次の質問へスクロール
                if (index < questionBlocks.length - 1) {
                    const nextBlock = questionBlocks[index + 1];
                    setTimeout(() => {
                        nextBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 300); // 0.3秒後にスクロール
                }
            });
        });
    });

    function calculateGAD7Score() {
        let score = 0;
        const totalQuestions = 7;
        const formData = new FormData(gad7Form);
        
        // 全ての質問に回答したかチェック
        if (Array.from(formData.keys()).length < totalQuestions) {
            displayErrorMessage("すべての質問に回答してください。");
            return;
        }
        
        formData.forEach(value => {
            score += parseInt(value);
        });

        displayResult(score);
    }

    function displayResult(score) {
        let resultText, adviceText, icon, resultClass;

        if (score >= 0 && score <= 4) {
            resultText = "不安は最小レベルです";
            adviceText = "現在の状態は良好です。この調子で、日々のリフレッシュを大切にしましょう。";
           
            resultClass = "result-minimal";
       } else if (score >= 5 && score <= 9) {
            resultText = "軽度の不安";
            adviceText = "軽度の不安を感じているようです。深呼吸や散歩など、簡単なリラクゼーションを試してみましょう。信頼できる人に話すのも良い方法です。";
            icon = "sentiment_satisfied";
            resultClass = "result-mild";
        } else if (score >= 10 && score <= 14) {
            resultText = "中等度の不安";
            adviceText = "不安が日常生活に影響を与え始めているかもしれません。一人で抱え込まず、教員やカウンセラーへの相談を検討することをお勧めします。";
            icon = "sentiment_dissatisfied";
            resultClass = "result-moderate";
         } else if (score >= 15 && score <= 21) {
            resultText = "重度の不安";
            adviceText = "専門的なサポートが必要なレベルの不安かもしれません。できるだけ早く、心療内科や精神科の専門医に相談してください。";
            icon = "sentiment_very_dissatisfied";
            resultClass = "result-severe";
        }

        // --- ここが重要 ---
        // 取得したURL変数を埋め込む
        resultDisplay.innerHTML = `
            <div class="result-content ${resultClass}">
                <span class="material-symbols-outlined result-icon">${icon}</span>
                <p class="result-score">合計スコア: <strong>${score}点</strong></p>
                <h3 class="result-diagnosis">${resultText}</h3>
                <p class="result-advice">${adviceText}</p>
                <div class="result-actions">
                    <a href="${takecareUrl}" class="action-button small-button">セルフケアのヒント</a>
                    <a href="${soudanUrl}" class="action-button small-button">教員・カウンセラーに相談</a>
                    <a href="${seishinkaUrl}" class="action-button small-button">精神科・心療内科の情報</a>
                </div>
                <div class="result-actions">
                    <a href="${homeUrl}" class="action-button small-button secondary">ホームに戻る</a>
                    <button onclick="window.location.reload();" class="action-button small-button secondary">もう一度チェックする</button>
                </div>
                <p class="disclaimer">
                    ※このチェックはあくまで目安であり、医学的な診断ではありません。<br>
                    心の不調が続く場合は、必ず専門家にご相談ください。
                </p>
            </div>
        `;
        resultDisplay.style.display = 'block';
    }

    function displayErrorMessage(message) {
        resultDisplay.innerHTML = `
            <div class="result-content result-error">
                <span class="material-symbols-outlined result-icon">error</span>
                <p class="result-advice">${message}</p>
            </div>
        `;
        resultDisplay.style.display = 'block';
    }
});
