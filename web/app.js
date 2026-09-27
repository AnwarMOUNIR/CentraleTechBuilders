import { createVoice } from './voice.js';

const $ = id => document.getElementById(id);
const state = { state: 'REQUEST', basket: [], pending: null, restaurant_id: 'demo', conversation_id: crypto.randomUUID() };
function debugEvent(speaker, text) {
  return fetch('/conversation-events', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({conversation_id:state.conversation_id, speaker, text}) }).catch(() => {});
}
let catalog = [], busy = false, session = false, generation = 0, blocked = false, speaking = false;
let restaurantLocked = false, autoListen = false, operation;
let modelDriven = false;
const autoListenKey = 'clearorder.autoListen';
let lastReply = 'Welcome to ClearOrder. Start a voice session, or type an order. Say help to hear the menu. All orders are simulated.';
const voice = createVoice(status);
const money = n => new Intl.NumberFormat('en', { maximumFractionDigits: 2 }).format(n) + ' MAD';
const normalize = s => s.toLowerCase().replace(/[^a-z0-9 ]/g, '').trim();
function restaurant() { return catalog.find(r => r.id === state.restaurant_id); }
function savedAutoListen() {
  try { return localStorage.getItem(autoListenKey) === 'true'; }
  catch { return false; }
}
function status(text) { $('status').textContent = text; }
async function readAloud(text) {
  debugEvent('playback', text);
  speaking = true; controls();
  try { await voice.speak(text); }
  finally { speaking = false; controls(); }
}
function controls() {
  $('send-button').disabled = busy || session;
  $('request-text').disabled = session;
  $('auto-listen').disabled = busy || session || !catalog.length;
  $('listen-button').disabled = busy && !session;
  $('listen-button').textContent = session ? 'Stop listening' : 'Start listening';
  $('listen-button').setAttribute('aria-pressed', String(session));
  $('confirm-button').disabled = busy || session || blocked || state.state !== 'REVIEW' || !state.basket.length || Boolean(state.pending);
  $('change-button').disabled = busy || session || !state.basket.length || ['CONFIRMED', 'CANCELLED'].includes(state.state);
  $('cancel-button').disabled = busy || session || ['CONFIRMED', 'CANCELLED'].includes(state.state) || !(state.basket.length || state.pending);
  $('repeat-button').disabled = busy || session;
  $('stop-speaking-button').disabled = !speaking;
  $('ordering-app').dataset.state = state.state;
  $('confirmation-hint').textContent = state.state === 'REVIEW' && !blocked && !state.pending
    ? 'Say “confirm order” after reviewing the basket, or use the confirmation button.'
    : 'Complete your order and review the exact total before confirming.';
}
function render(result) {
  for (const key of ['state', 'basket', 'pending']) state[key] = result[key];
  if (result.restaurant_id && result.restaurant_id !== state.restaurant_id) {
    state.restaurant_id = result.restaurant_id;
    updateRestaurantDisplay(result.restaurant_id);
  }
  lastReply = result.reply_text;
  if (result.question && !lastReply.includes(result.question)) lastReply += ' ' + result.question;
  $('response').textContent = lastReply;
  const allProducts = catalog.flatMap(r => r.menu);
  $('basket').replaceChildren();
  for (const line of state.basket) {
    const product = allProducts.find(p => p.id === line.product_id);
    const options = line.modifier_ids.map(id => product?.modifiers?.find(m => m.id === id)?.label || id).join(', ');
    const li = document.createElement('li');
    li.textContent = `${line.quantity} × ${product?.name || line.product_id}${options ? ' — ' + options : ''}: ${money(line.line_total_mad)}`;
    $('basket').append(li);
  }
  if (!state.basket.length) {
    const li = document.createElement('li'); li.textContent = 'Your basket is empty.'; $('basket').append(li);
  }
  $('total').textContent = money(result.total_mad);
  blocked = Boolean(result.error);
  controls();
}
function updateRestaurantDisplay(id) {
  const r = catalog.find(x => x.id === id);
  if (r) {
    if ($('restaurant-name')) $('restaurant-name').textContent = r.name;
    const estimate = r.delivery?.estimate_min_minutes;
    const delivery = estimate ? ` Published delivery estimate: ${estimate}–${r.delivery.estimate_max_minutes} minutes; not a live quote.` : '';
    if ($('restaurant-note')) $('restaurant-note').textContent = r.note + delivery + ' Displayed totals are food subtotals; delivery and other fees are excluded.';
  }
}
function selectRestaurant(id) {
  state.restaurant_id = id;
  restaurantLocked = true;
  updateRestaurantDisplay(id);
  lastReply = `Selected ${restaurant().name}. Your existing items are preserved. What would you like to add?`;
  $('response').textContent = lastReply;
}
function stopSession(message = 'Voice session stopped. Your basket is still here.') {
  session = false; generation++; operation?.abort(); voice.stop(); busy = false;
  status(message); controls(); $('listen-button').focus();
}
async function requestRecommendation(text, turn) {
  operation = new AbortController();
  const response = await fetch('/recommend', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text.trim(), conversation_id: state.conversation_id }),
    signal: AbortSignal.any([operation.signal, AbortSignal.timeout(65000)]) });
  if (!response.ok) throw new Error('Restaurant matching is unavailable. Please retry.');
  const result = await response.json();
  if (turn !== generation) return true;
  if (!result.matched) return false;
  state.restaurant_id = result.restaurant_id;
  updateRestaurantDisplay(result.restaurant_id);
  render(result);
  return true;
}
async function interpretText(text, turn) {
  operation = new AbortController();
  const response = await fetch('/interpret', { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: text.trim(), ...state }),
    signal: AbortSignal.any([operation.signal, AbortSignal.timeout(85000)]) });
  if (!response.ok) throw new Error('The ordering service could not process this request. Please retry.');
  const result = await response.json();
  if (turn === generation) render(result);
}
async function submit(text, fromVoice = false) {
  if (busy || !text.trim()) return;
  if (['stop listening', 'stop voice session', 'stop'].includes(normalize(text))) { debugEvent('user', text); stopSession(); return; }
  const turn = generation;
  busy = true; controls(); status('Processing your request…');
  try {
    if (modelDriven) {
      await interpretText(text, turn);
    } else if (normalize(text) === 'restaurants' || normalize(text) === 'list restaurants') {
      debugEvent('user', text);
      lastReply = 'Say choose followed by a restaurant name, or tell me the items you want and I will find a menu match. ' + catalog.map(r => r.name).join('. ');
      $('response').textContent = lastReply;
      debugEvent('assistant', lastReply);
    } else if (/^(choose|select|switch to|change (?:the )?restaurant to|go to)\b/i.test(text)) {
      debugEvent('user', text);
      const found = catalog.find(r => normalize(text).includes(normalize(r.name)) ||
        (r.id === 'demo' && normalize(text).includes('demo')));
      if (found) selectRestaurant(found.id, true);
      else if (!state.basket.length && /^(choose|select|switch to)\s+(?:the\s+)?(?:best|cheapest)\b/i.test(text)) {
        if (!await requestRecommendation(text, turn)) {
          lastReply = 'I could not match those items. Say help to hear the menu.';
          $('response').textContent = lastReply;
        }
      } else { lastReply = 'Please say restaurants to hear the available names.'; $('response').textContent = lastReply; }
      debugEvent('assistant', lastReply);
    } else {
      const startsNewOrder = !state.basket.length || ['CONFIRMED', 'CANCELLED'].includes(state.state);
      const menuRequest = ['help', 'menu', 'read menu', 'what can i order'].includes(normalize(text));
      if (!restaurantLocked && startsNewOrder && !menuRequest) {
        const recommended = await requestRecommendation(text, turn);
        if (!recommended) {
          await interpretText(text, turn);
        }
      } else {
        await interpretText(text, turn);
      }
    }
    if (turn !== generation) return;
    status('Response ready.');
    if (fromVoice || $('read-aloud').checked) { voice.preparePlayback(); status('Speaking…'); await readAloud(lastReply); }
  } catch (error) {
    if (turn !== generation) return;
    debugEvent('error', error.message);
    blocked = true;
    if (session) stopSession('Voice session paused: ' + error.message);
    else status(error.message);
  } finally {
    if (turn === generation) { busy = false; controls(); }
  }
}
async function startSession() {
  if (session) { stopSession(); return; }
  session = true; const turn = ++generation; controls();
  try {
    status('Allow microphone access to begin.');
    await voice.start();
    if (turn !== generation) return;
    status('Speaking…'); await readAloud('I am listening now. Tell me anything you would like to order. I will read it back with the total so you can confirm or cancel.');
    let silences = 0;
    while (session && turn === generation) {
      await new Promise(resolve => setTimeout(resolve, 300));
      if (!session || turn !== generation) break;
      status('Listening — speak now.');
      let text;
      try {
        text = await voice.listen();
        silences = 0;
      } catch (error) {
        if (turn !== generation || !session) break;
        debugEvent('error', error.message);
        if (error.message.startsWith('Voice session stopped')) break;
        silences++;
        status('Still listening… Say your order whenever you are ready.');
        if (silences % 3 === 0) {
          status('Speaking…');
          await readAloud('I am still listening. Tell me what you would like to order or ask about the menu.');
        }
        await new Promise(resolve => setTimeout(resolve, 600));
        continue;
      }
      if (turn !== generation || !session) break;
      $('request-text').value = text;
      $('transcript').textContent = 'Heard: ' + text;
      await submit(text, true);
      if (session && ['CONFIRMED', 'CANCELLED'].includes(state.state)) {
        stopSession('Voice session finished. Start another session for a new order.');
      }
    }
  } catch (error) { if (turn === generation) stopSession(error.message); }
}

$('send-button').addEventListener('click', () => submit($('request-text').value));
$('request-text').addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(e.target.value); } });
$('listen-button').addEventListener('click', startSession);
$('auto-listen').addEventListener('change', event => {
  autoListen = event.target.checked;
  try { localStorage.setItem(autoListenKey, String(autoListen)); }
  catch {
    autoListen = false; event.target.checked = false;
    status('Auto-start could not be saved. Use Start voice session instead.');
    return;
  }
  if (autoListen && catalog.length) startSession();
});
$('stop-speaking-button').addEventListener('click', () => { voice.stopPlayback(); status('Playback stopped.'); });
$('repeat-button').addEventListener('click', async () => {
  busy = true; controls();
  try { voice.preparePlayback(); await readAloud(lastReply); }
  catch (error) { status(error.message); }
  finally { voice.stop(); busy = false; controls(); }
});
$('confirm-button').addEventListener('click', () => submit('confirm order'));
$('change-button').addEventListener('click', () => { submit('change'); $('request-text').focus(); });
$('cancel-button').addEventListener('click', () => submit('cancel'));
document.addEventListener('keydown', e => { if (e.key === 'Escape') stopSession(); });
window.addEventListener('pagehide', () => voice.stop());

async function initialize() {
  autoListen = savedAutoListen();
  $('auto-listen').checked = autoListen;
  busy = true; controls();
  try {
    const response = await fetch('/catalog', { signal: AbortSignal.timeout(8000) });
    if (!response.ok) throw new Error('Start the API server, then reload this page.');
    catalog = await response.json();
    $('menu-list').replaceChildren();
    for (const r of catalog) {
      const section = document.createElement('li');
      section.style.marginBlock = '8px';
      section.innerHTML = `<strong>${r.name}</strong> <span style="font-size:0.85em; opacity:0.8;">(${r.menu.length} items)</span>`;
      const ul = document.createElement('ul');
      ul.style.marginTop = '4px';
      for (const p of r.menu) {
        const item = document.createElement('li');
        item.textContent = `${p.name} — ${money(p.base_price_mad)}`;
        ul.append(item);
      }
      section.append(ul);
      $('menu-list').append(section);
    }
    updateRestaurantDisplay('demo');
    const health = await (await fetch('/health')).json();
    modelDriven = health.mode !== 'mock';
    $('mode').textContent = health.mode === 'mock' ? 'Demo interpreter (offline rules)' : `Local Ollama model: ${health.model}`;
    await voice.initialize();
    status('Ready. Start a voice session or type your order.');
  } catch (error) { status(error.message); }
  finally {
    busy = false; controls();
    if (!catalog.length) { $('send-button').disabled = true; $('listen-button').disabled = true; }
    else if (autoListen) startSession();
  }
}
initialize();
