"""Streamlit-фронт для AI-тренажёра.

Запуск:
    streamlit run frontend/app.py

Бэкенд должен быть поднят на http://localhost:8000.
"""
from __future__ import annotations

import uuid
from typing import Any

import requests
import streamlit as st

API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="AI-тренажёр",
    page_icon="🎓",
    layout="wide",
)

if "anon_id" not in st.session_state:
    st.session_state.anon_id = f"anon-{uuid.uuid4().hex[:12]}"
if "session" not in st.session_state:
    st.session_state.session = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "scenarios" not in st.session_state:
    st.session_state.scenarios = None


def fetch_scenarios() -> list[dict[str, Any]]:
    try:
        r = requests.get(f"{API_BASE}/api/scenarios", timeout=5)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Не удалось получить сценарии: {e}")
        return []


def create_session(scenario_slug: str, mode: str) -> dict[str, Any] | None:
    try:
        r = requests.post(
            f"{API_BASE}/api/dialog/sessions",
            json={
                "scenario_slug": scenario_slug,
                "mode": mode,
                "anonymous_id": st.session_state.anon_id,
            },
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Ошибка создания сессии: {e}")
        return None


def send_message(session_id: str, content: str) -> dict[str, Any] | None:
    try:
        r = requests.post(
            f"{API_BASE}/api/dialog/sessions/{session_id}/messages",
            json={"content": content},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        st.error(f"Ошибка отправки сообщения: {e}")
        return None


def download_pdf(session_id: str) -> bytes | None:
    try:
        r = requests.get(
            f"{API_BASE}/api/dialog/sessions/{session_id}/export.pdf",
            timeout=15,
        )
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        st.error(f"Ошибка экспорта PDF: {e}")
        return None


# ---------- sidebar ----------

with st.sidebar:
    st.header("Параметры сессии")

    if st.session_state.scenarios is None:
        st.session_state.scenarios = fetch_scenarios()

    scenarios = st.session_state.scenarios
    if not scenarios:
        st.warning("Бэкенд недоступен или сценарии не загружены.")
        st.stop()

    slug_to_title = {s["slug"]: s["title"] for s in scenarios}
    scenario_slug = st.selectbox(
        "Сценарий",
        options=list(slug_to_title.keys()),
        format_func=lambda s: slug_to_title[s],
    )
    mode = st.radio(
        "Режим",
        options=["info", "trainer"],
        format_func=lambda m: "Информация" if m == "info" else "Тренажёр",
    )

    if st.button("Новая сессия", type="primary", use_container_width=True):
        session = create_session(scenario_slug, mode)
        if session:
            st.session_state.session = session
            st.session_state.messages = [
                {"role": "assistant", "content": session["initial_message"]}
            ]

    st.divider()
    st.caption(f"Анонимный id: `{st.session_state.anon_id}`")
    st.caption("Дисклеймер: рекомендации носят информационный характер.")

    if st.session_state.session:
        st.divider()
        if st.button("Скачать PDF", use_container_width=True):
            pdf_bytes = download_pdf(st.session_state.session["id"])
            if pdf_bytes:
                st.download_button(
                    label="Скачать отчёт",
                    data=pdf_bytes,
                    file_name=f"session-{st.session_state.session['id']}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

# ---------- main ----------

st.title("🎓 AI-тренажёр для абитуриента и стажёра")

if st.session_state.session is None:
    st.info("Выберите сценарий и режим в боковой панели, затем нажмите «Новая сессия».")
    st.stop()

session = st.session_state.session
st.caption(
    f"Сессия `{session['id']}` · сценарий `{session['scenario_slug']}` · "
    f"режим `{session['mode']}` · состояние `{session['state']}`"
)

# отрисовать историю
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citations"):
            with st.expander("Источники"):
                for c in msg["citations"]:
                    st.markdown(f"- [{c['title'] or c['url']}]({c['url']}) · _{c['type']}_ · chunk #{c['chunk_index']}")
        if msg.get("evaluation"):
            ev = msg["evaluation"]
            color = {"good": "🟢", "needs_improvement": "🟡", "incomplete": "🔴"}[ev["verdict"]]
            st.markdown(f"{color} **Вердикт:** `{ev['verdict']}` · score `{ev['score']}`")
            if ev["mistakes"]:
                st.markdown("**Типовые ошибки:** " + ", ".join(ev["mistakes"]))
            if ev["improvements"]:
                st.markdown(f"**Что улучшить:** {ev['improvements']}")
            if ev["exemplar"]:
                with st.expander("Удачный пример ответа"):
                    st.markdown(ev["exemplar"])

# ---------- ввод ----------
if session["state"] == "finished":
    st.success("Сессия завершена. Создайте новую, чтобы пройти сценарий ещё раз.")
    st.stop()

# Кнопка голосового ввода (использует браузерный Web Speech API)
# Она обновляет скрытое текстовое поле, которое мы будем читать.
st.write("👇 Голосовой ввод (работает в Chrome и Edge):")
st.html(
    """
    <div id="voice-container">
        <button id="start-btn" style="padding: 10px 20px; background-color: #ff4b4b; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">🎤 Говорить</button>
        <p id="status" style="color: gray; margin-top: 5px;">Нажмите, чтобы начать</p>
    </div>
    <script>
        const startBtn = document.getElementById('start-btn');
        const status = document.getElementById('status');
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (SpeechRecognition) {
            const recognition = new SpeechRecognition();
            recognition.lang = 'ru-RU';
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            startBtn.onclick = () => {
                recognition.start();
                startBtn.style.backgroundColor = '#4CAF50';
                status.innerText = 'Слушаю...';
            };

            recognition.onresult = (event) => {
                const text = event.results[0][0].transcript;
                status.innerText = 'Распознано: ' + text;
                
                // Отправляем текст в Streamlit через API
                const streamlitInput = window.parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
                if (streamlitInput) {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(streamlitInput, text);
                    streamlitInput.dispatchEvent(new Event('input', { bubbles: true }));
                    // Фокусируемся и жмем Enter (Streamlit обрабатывает Enter)
                    streamlitInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true }));
                }
            };

            recognition.onerror = (event) => {
                status.innerText = 'Ошибка: ' + event.error;
                startBtn.style.backgroundColor = '#ff4b4b';
            };

            recognition.onend = () => {
                startBtn.style.backgroundColor = '#ff4b4b';
                if (status.innerText === 'Слушаю...') status.innerText = 'Готово';
            };
        } else {
            status.innerText = 'Ваш браузер не поддерживает голосовой ввод.';
        }
    </script>
    """
)

# стандартный чат-инпут
user_input = st.chat_input("Или введите текстом…")
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Думаю…"):
            resp = send_message(session["id"], user_input)

    if resp:
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": resp["content"],
                "evaluation": resp.get("evaluation"),
                "citations": resp.get("citations"),
            }
        )
        st.session_state.session["state"] = resp["state"]
        st.rerun()