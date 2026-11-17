// peace.js
// サイト共通の小さなUI。各機能は、その要素があるページでだけ動く。
//   - ホーム: 時間帯に合わせたあいさつ / 呼吸ガイド / 今の気持ち
//   - セルフチェック: 回答の進み具合バー
// どれもブラウザ内だけで完結し、何も保存・送信しない。
// 文章は gettext() で翻訳される（翻訳は mentalhealth/locale/<言語>/LC_MESSAGES/djangojs.po）。

document.addEventListener("DOMContentLoaded", () => {
    setupGreeting();
    setupTodayWord();
    setupBreathing();
    setupMood();
    setupQuizProgress();
});

function setupGreeting() {
    const el = document.getElementById("greeting");
    if (!el) return;
    const h = new Date().getHours();
    if (h >= 5 && h < 11) el.textContent = gettext("おはようございます");
    else if (h >= 11 && h < 17) el.textContent = gettext("こんにちは");
    else if (h >= 17 && h < 23) el.textContent = gettext("こんばんは。今日もおつかれさま");
    else el.textContent = gettext("夜おそくまで、おつかれさま");
}

// 今日のことば：日付ごとに1つ選ぶ（同じ日なら何度開いても同じことば）
const TODAY_WORDS = [
    gettext("がんばれない日があっても、あなたの価値は変わりません。"),
    gettext("休むことも、前に進むことのひとつです。"),
    gettext("今日はここまで来られただけで、じゅうぶんです。"),
    gettext("完璧じゃなくていい。いまのあなたで大丈夫。"),
    gettext("つらいと言えることは、弱さではなく強さです。"),
    gettext("ゆっくりでいい。比べなくていい。"),
    gettext("深呼吸をひとつ。それだけで今日は合格です。"),
    gettext("あなたの気持ちは、あなたが思うより大切にされていい。"),
    gettext("雨の日があるから、晴れの日に気づけます。"),
    gettext("助けを求めるのは、自分を大切にするということ。"),
    gettext("小さな「できた」を、ひとつ数えてみましょう。"),
    gettext("眠れなかった夜も、ちゃんと朝はきます。"),
    gettext("誰かにやさしくするように、自分にもやさしく。"),
    gettext("立ち止まっている時間も、あなたの大事な時間です。"),
];

function setupTodayWord() {
    const el = document.getElementById("todayWord");
    if (!el) return;
    const now = new Date();
    const dayNumber = Math.floor((now - new Date(now.getFullYear(), 0, 0)) / 86400000);
    el.textContent = TODAY_WORDS[dayNumber % TODAY_WORDS.length];
}

// 呼吸ガイド：ボタンを押したときだけ動く（勝手に動くアニメーションは使わない）
// 「4秒すう → 2秒とめる → 6秒はく」を5回（=1分）くり返して、自動で終わる。
function setupBreathing() {
    const root = document.getElementById("breath");
    const toggle = document.getElementById("breathToggle");
    if (!root || !toggle) return;

    const ROUNDS = 5;
    const phases = [
        { key: "in", text: gettext("すって"), seconds: 4 },
        { key: "hold", text: gettext("とめて"), seconds: 2 },
        { key: "out", text: gettext("はいて"), seconds: 6 },
    ];
    const text = document.getElementById("breathText");
    const count = document.getElementById("breathCount");
    const label = document.getElementById("breathToggleLabel");
    const icon = toggle.querySelector(".material-symbols-outlined");
    const caption = document.getElementById("breathCaption");
    const circle = root.querySelector(".breath-circle");
    const steps = root.querySelectorAll(".breath-steps li");
    const idleText = text.innerHTML;

    let ticker = null;
    let phaseIndex = 0;
    let round = 1;
    let remaining = 0;

    function setButton(iconName, labelText, pressed) {
        icon.textContent = iconName;
        label.textContent = labelText;
        toggle.setAttribute("aria-pressed", String(pressed));
    }

    function highlight(key) {
        steps.forEach((li) => li.classList.toggle("is-current", li.dataset.step === key));
    }

    function enterPhase() {
        const phase = phases[phaseIndex];
        root.dataset.phase = phase.key;
        circle.style.transitionDuration = phase.key === "hold" ? "0.3s" : `${phase.seconds}s`;
        text.textContent = phase.text;
        remaining = phase.seconds;
        count.textContent = remaining;
        highlight(phase.key);
        caption.textContent = interpolate(gettext("%(round)s / %(total)s 回目"), { round: round, total: ROUNDS }, true);
    }

    function tick() {
        remaining -= 1;
        if (remaining > 0) {
            count.textContent = remaining;
            return;
        }
        phaseIndex += 1;
        if (phaseIndex === phases.length) {
            phaseIndex = 0;
            round += 1;
            if (round > ROUNDS) {
                finish();
                return;
            }
        }
        enterPhase();
    }

    function reset(phaseName) {
        clearInterval(ticker);
        ticker = null;
        root.dataset.phase = phaseName;
        circle.style.transitionDuration = "1.2s";
        count.textContent = "";
        highlight(null);
    }

    function start() {
        phaseIndex = 0;
        round = 1;
        setButton("pause", gettext("とちゅうでやめる"), true);
        enterPhase();
        ticker = setInterval(tick, 1000);
    }

    function finish() {
        reset("done");
        text.textContent = gettext("おつかれさま");
        caption.textContent = gettext("1分間の呼吸ができました。さっきより少し、体がゆるんでいたらうれしいです。");
        setButton("replay", gettext("もう1分やる"), false);
    }

    function stop() {
        reset("idle");
        text.innerHTML = idleText;
        caption.textContent = gettext("とちゅうでも大丈夫。いつでも、また始められます。");
        setButton("play_arrow", gettext("はじめる（1分）"), false);
    }

    toggle.addEventListener("click", () => (ticker ? stop() : start()));

    // 「今の気持ち」の返事などから呼び出せるようにする
    document.addEventListener("breath:start", () => {
        root.scrollIntoView({ behavior: "smooth", block: "center" });
        if (!ticker) start();
    });
}

// 今の気持ち：選ぶと、ボタンがふわっと反応し、気持ちに合わせた一言と次の一歩を出す（保存しない）
function setupMood() {
    const section = document.querySelector(".mood");
    const reply = document.getElementById("moodReply");
    if (!section || !reply) return;

    const { soudanUrl, aiUrl, takecareUrl, stressUrl } = section.dataset;
    const BREATH = "breath";
    const replies = {
        1: {
            icon: "favorite",
            title: gettext("教えてくれて、ありがとう"),
            text: gettext("とてもつらいときに、ここに来てくれたこと。それだけで大切な一歩です。ひとりで抱えなくて大丈夫。今すぐ話を聞いてもらえる場所もあります。"),
            links: [[gettext("先生に相談する"), soudanUrl], [gettext("1分だけ呼吸する"), BREATH], [gettext("今すぐ電話で話す"), "#help"]],
        },
        2: {
            icon: "volunteer_activism",
            title: gettext("しんどい中、よく来ましたね"),
            text: gettext("まずは1分、ゆっくり息をはいてみませんか。言葉にできそうなら、だれかに話すと少し軽くなることがあります。"),
            links: [[gettext("1分だけ呼吸する"), BREATH], [gettext("先生に相談する"), soudanUrl], [gettext("AIに話してみる"), aiUrl]],
        },
        3: {
            icon: "cloud",
            title: gettext("もやもやする日もありますよね"),
            text: gettext("何が気になっているのか、少しだけ整理してみると、もやもやの正体が見えてくるかもしれません。"),
            links: [[gettext("ストレスチェック"), stressUrl], [gettext("AIに話してみる"), aiUrl]],
        },
        4: {
            icon: "spa",
            title: gettext("「まあまあ」も、大切な状態です"),
            text: gettext("元気なうちに、自分をいたわる時間を少しとっておくと、しんどい日の支えになります。"),
            links: [[gettext("セルフケアのヒント"), takecareUrl], [gettext("1分だけ呼吸する"), BREATH]],
        },
        5: {
            icon: "sunny",
            title: gettext("いい感じなんですね。うれしいです"),
            text: gettext("その気持ちを大事にしてください。今日の「よかったこと」を1つ思い出してみると、もっと長持ちします。"),
            links: [[gettext("セルフケアのヒント"), takecareUrl]],
        },
    };

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // 押したボタンから、葉っぱ色の小さな粒がふわっと舞い上がる（押したときだけ・1秒で消える）
    function sparkle(button) {
        if (reduceMotion) return;
        for (let i = 0; i < 8; i++) {
            const dot = document.createElement("span");
            dot.className = "mood-spark";
            dot.style.setProperty("--dx", `${Math.round((Math.random() - 0.5) * 90)}px`);
            dot.style.setProperty("--dy", `${Math.round(-40 - Math.random() * 50)}px`);
            dot.style.setProperty("--s", (0.6 + Math.random() * 0.7).toFixed(2));
            dot.style.animationDelay = `${Math.round(Math.random() * 120)}ms`;
            dot.addEventListener("animationend", () => dot.remove());
            button.appendChild(dot);
        }
    }

    function render(mood) {
        const r = replies[mood];
        reply.replaceChildren();

        const head = document.createElement("div");
        head.className = "mood-reply-head";
        const ic = document.createElement("span");
        ic.className = "material-symbols-outlined mood-reply-icon";
        ic.setAttribute("aria-hidden", "true");
        ic.textContent = r.icon;
        const title = document.createElement("strong");
        title.textContent = r.title;
        head.append(ic, title);

        const p = document.createElement("p");
        p.textContent = r.text;

        const actions = document.createElement("div");
        actions.className = "reply-actions";
        r.links.forEach(([text, href], i) => {
            const el = document.createElement(href === BREATH ? "button" : "a");
            el.className = i === 0 ? "btn btn--small" : "btn btn--ghost btn--small";
            el.textContent = text;
            if (href === BREATH) {
                el.type = "button";
                el.addEventListener("click", () => document.dispatchEvent(new Event("breath:start")));
            } else {
                el.href = href;
            }
            actions.appendChild(el);
        });

        reply.append(head, p, actions);
        reply.hidden = false;
        // 同じ気持ちを選び直したときも、もう一度ふわっと表示させる
        reply.classList.remove("is-shown");
        void reply.offsetWidth;
        reply.classList.add("is-shown");
        reply.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
    }

    const buttons = section.querySelectorAll(".mood-option");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
            button.classList.remove("is-popping");
            void button.offsetWidth;
            button.classList.add("is-popping");
            sparkle(button);
            render(button.dataset.mood);
        });
    });
}

// セルフチェック：何問中何問に答えたかを上部のバーに表示する
function setupQuizProgress() {
    const bar = document.querySelector("[data-quiz-progress]");
    const form = document.querySelector("form.quiz");
    if (!bar || !form) return;

    const blocks = form.querySelectorAll(".question-block");
    const fill = bar.querySelector(".quiz-progress-bar span");
    const label = bar.querySelector(".quiz-progress-text");

    function update() {
        const answered = Array.from(blocks).filter((b) => b.querySelector("input:checked")).length;
        fill.style.width = `${(answered / blocks.length) * 100}%`;
        label.textContent = answered === blocks.length
            ? gettext("すべて回答しました")
            : interpolate(gettext("%(answered)s / %(total)s 問"), { answered: answered, total: blocks.length }, true);
    }

    form.addEventListener("change", update);
    update();
}
