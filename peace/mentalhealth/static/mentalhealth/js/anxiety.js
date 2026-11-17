document.addEventListener("DOMContentLoaded", () => {
    const gad7Form = document.getElementById('gad7Form');
    const questionBlocks = document.querySelectorAll('.question-block');
    const checkerSection = document.getElementById('anxiety-checker-section');

    // フォーム送信時の処理（スコアを計算して結果ページへ遷移する）
    if (gad7Form) {
        gad7Form.addEventListener('submit', (e) => {
            e.preventDefault(); // ページのリロードを防止
            calculateGAD7Score();
        });
    }

    // 各質問ブロックにクリックイベントを追加して自動スクロール
    questionBlocks.forEach((currentBlock, index) => {
        const radios = currentBlock.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
            radio.addEventListener('change', () => {
                if (index < questionBlocks.length - 1) {
                    const nextBlock = questionBlocks[index + 1];
                    setTimeout(() => {
                        nextBlock.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 200);
                }
            });
        });
    });

    // GAD-7スコアを計算し、結果ページへスコア付きで遷移する
    function calculateGAD7Score() {
        let score = 0;
        const totalQuestions = 7;
        const formData = new FormData(gad7Form);

        // 全ての質問に回答したかチェック
        if (Array.from(formData.keys()).length < totalQuestions) {
            alert(gettext("すべての質問に回答してください。"));
            return;
        }

        formData.forEach(value => {
            score += parseInt(value, 10);
        });

        // Django側の {% url %} で発行されたURLに、スコアを付けて遷移する
        const resultBaseUrl = checkerSection.dataset.resultUrl;
        window.location.href = `${resultBaseUrl}?score=${score}`;
    }
});
