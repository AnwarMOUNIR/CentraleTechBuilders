const state = {
  basket: [],
  state: "REQUEST",
  pending: null,
  lastReply: "",
};

const byId = (id) => document.getElementById(id);

let speech = {
  listen: async () => { throw new Error("Speech recognition is not available yet. Please type your order."); },
  speak: () => {},
  stopSpeaking: () => {},
  speechAvailable: () => ({ listen: false, speak: false }),
};

async function loadSpeechAdapter() {
  const mock = new URLSearchParams(window.location.search).get("mockSpeech") === "true";
  try {
    speech = await import(mock ? "./speech.mock.js" : "./speech.js");
  } catch {
    // The text path remains usable while the speech contributor is working.
  }
  const availability = speech.speechAvailable();
  const listenButton = byId("listen-button");
  if (listenButton) listenButton.disabled = !availability.listen;
  const repeatButton = byId("repeat-button");
  if (repeatButton) repeatButton.disabled = !availability.speak;
  const stopButton = byId("stop-speaking-button");
  if (stopButton) stopButton.disabled = !availability.speak;
}

function setStatus(message) {
  const element = byId("status");
  if (element) element.textContent = message;
}

function render(result) {
  state.state = result.state;
  state.basket = result.basket;
  state.pending = result.pending;
  state.lastReply = result.reply_text;

  const response = byId("response");
  if (response) response.textContent = result.reply_text;

  const basket = byId("basket");
  if (basket) {
    basket.replaceChildren();
    for (const line of result.basket) {
      const item = document.createElement("li");
      const modifiers = line.modifier_ids.length ? ` (${line.modifier_ids.join(", ")})` : "";
      item.textContent = `${line.quantity} × ${line.product_id}${modifiers} — ${line.line_total_mad} MAD`;
      basket.append(item);
    }
    const total = document.createElement("li");
    total.textContent = `Total: ${result.total_mad} MAD`;
    total.className = "basket-total";
    basket.append(total);
  }

  setStatus(result.error || `Status: ${result.state}`);
  speech.speak(result.reply_text);
}

async function submit(text) {
  const cleanText = text.trim();
  if (!cleanText) {
    setStatus("Type or speak an order.");
    return;
  }

  setStatus("Processing…");
  try {
    const response = await fetch("/interpret", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: cleanText,
        basket: state.basket,
        state: state.state,
        pending: state.pending,
      }),
    });
    if (!response.ok) throw new Error(`API error ${response.status}`);
    render(await response.json());
  } catch (error) {
    setStatus(`Unable to contact the service: ${error.message}`);
  }
}

function bindEvents() {
  const input = byId("request-text");
  byId("send-button")?.addEventListener("click", () => submit(input?.value || ""));
  input?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") submit(input.value);
  });
  byId("listen-button")?.addEventListener("click", async () => {
    setStatus("Listening…");
    try {
      const transcript = await speech.listen();
      if (input) input.value = transcript;
      await submit(transcript);
    } catch (error) {
      setStatus(error.message);
    }
  });
  byId("repeat-button")?.addEventListener("click", () => speech.speak(state.lastReply));
  byId("stop-speaking-button")?.addEventListener("click", () => {
    speech.stopSpeaking();
    setStatus("Speech playback stopped.");
  });
  byId("confirm-button")?.addEventListener("click", () => submit("confirm"));
  byId("change-button")?.addEventListener("click", () => {
    input?.focus();
    setStatus("Describe the change you want.");
  });
  byId("cancel-button")?.addEventListener("click", () => submit("cancel"));
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  await loadSpeechAdapter();
});

