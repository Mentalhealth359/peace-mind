// Firebase SDKs and main script logic
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-app.js";
import { getAuth, signInAnonymously, signInWithCustomToken, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/11.6.1/firebase-auth.js";
// ... (Firestore imports)

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const auth = getAuth(app);

let userId = null;
const userIdSpan = document.getElementById('userIdSpan');

onAuthStateChanged(auth, async (user) => {
    if (user) {
        userId = user.uid;
        userIdSpan.textContent = userId;
        initApp();
    } else {
        try {
            await signInAnonymously(auth);
            userId = auth.currentUser.uid;
            userIdSpan.textContent = userId;
            initApp();
        } catch (authError) {
            console.error("Firebase authentication failed:", authError);
        }
    }
});