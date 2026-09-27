let activeListenPromise = null;

function recognitionConstructor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function speechAvailable() {
  return {
    listen: Boolean(recognitionConstructor()),
    speak: typeof window !== "undefined" && "speechSynthesis" in window,
  };
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

export function speak(text) {
  if (!text || !speechAvailable().speak || typeof SpeechSynthesisUtterance === "undefined") return;

  stopSpeaking();
  const utterance = new SpeechSynthesisUtterance(String(text));
  utterance.lang = "en-US";
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function recognitionErrorMessage(code) {
  const messages = {
    "not-allowed": "Microphone access was denied. Allow microphone permission or type your order.",
    "service-not-allowed": "Speech recognition is blocked. Check browser permissions or type your order.",
    "no-speech": "No speech was detected. Please try again or type your order.",
    "audio-capture": "No working microphone was found. Connect one or type your order.",
    network: "Speech recognition could not reach its service. Check your connection or type your order.",
    aborted: "Speech recognition was stopped.",
  };
  return messages[code] || `Speech recognition failed (${code || "unknown error"}). Please type your order.`;
}

export async function listen() {
  if (activeListenPromise) return activeListenPromise;

  const Recognition = recognitionConstructor();
  if (!Recognition) {
    throw new Error("Speech recognition is not supported in this browser. Please type your order.");
  }

  stopSpeaking();
  activeListenPromise = new Promise((resolve, reject) => {
    const recognition = new Recognition();
    let settled = false;
    let transcript = "";

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      callback(value);
    };

    recognition.onresult = (event) => {
      transcript = event.results?.[0]?.[0]?.transcript?.trim() || "";
    };
    recognition.onerror = (event) => {
      finish(reject, new Error(recognitionErrorMessage(event.error)));
    };
    recognition.onend = () => {
      if (transcript) finish(resolve, transcript);
      else finish(reject, new Error("No speech was detected. Please try again or type your order."));
    };

    try {
      recognition.start();
    } catch (error) {
      finish(reject, new Error(`Unable to start speech recognition: ${error.message}`));
    }
  });

  try {
    return await activeListenPromise;
  } finally {
    activeListenPromise = null;
  }
}
