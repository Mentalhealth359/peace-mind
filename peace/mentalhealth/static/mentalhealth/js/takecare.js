document.addEventListener('DOMContentLoaded', () => {
    const tabButtons = document.querySelectorAll('.tab-button');
    const careGrids = document.querySelectorAll('.care-grid');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // クリックされたタブのdata-tab属性を取得
            const targetTab = button.dataset.tab;

            // すべてのボタンから 'active' クラスを削除
            tabButtons.forEach(btn => btn.classList.remove('active'));
            // クリックされたボタンに 'active' クラスを追加
            button.classList.add('active');

            // すべてのコンテンツグリッドから 'active' クラスを削除
            careGrids.forEach(grid => grid.classList.remove('active'));
            
            // 対応するコンテンツグリッドに 'active' クラスを追加
            const targetGrid = document.getElementById(`${targetTab}-content`);
            if (targetGrid) {
                targetGrid.classList.add('active');
            }
        });
    });
});
