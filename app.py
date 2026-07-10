"""
ASK AI v0.3 — A Square Innovations
Week 3: Multiple goals + burnout alert + deployment ready
"""

import os
import json
import datetime
import streamlit as st
from groq import Groq

MEMORY_FILE = 

# ─── EMOTION DETECTION ───────────────────────────────────────────────────────

STRESSED_WORDS = [
    "stressed", "anxious", "overwhelmed", "tired", "exhausted", "worried",
    "nervous", "scared", "frustrated", "confused", "lost", "stuck",
    "can't", "failing", "failed", "bad", "terrible", "awful", "pressure",
    "deadline", "panic", "hopeless", "give up", "burnout", "depressed", "empty"
]

MOTIVATED_WORDS = [
    "excited", "motivated", "happy", "great", "amazing", "confident",
    "ready", "focused", "determined", "inspired", "energetic", "positive",
    "progress", "achieved", "completed", "done", "winning", "proud",
    "good", "excellent", "fantastic", "let's go", "pumped", "crushing it"
]

GOAL_CATEGORIES = ["🚀 Startup", "📚 Studies", "💪 Fitness", "💰 Finance", "🎯 Personal"]

def detect_emotion(text):
    text_lower = text.lower()
    stress_score = sum(1 for word in STRESSED_WORDS if word in text_lower)
    motivation_score = sum(1 for word in MOTIVATED_WORDS if word in text_lower)
    if stress_score > motivation_score and stress_score > 0:
        return "stressed"
    elif motivation_score > stress_score and motivation_score > 0:
        return "motivated"
    return "neutral"

def emotion_emoji(emotion):
    return {"stressed": "😟", "motivated": "🔥", "neutral": "😊"}.get(emotion, "😊")

def mood_to_score(mood):
    return {"motivated": 3, "neutral": 2, "stressed": 1}.get(mood, 2)

# ─── BURNOUT DETECTION ───────────────────────────────────────────────────────

def check_burnout_risk(memory):
    """
    Returns: 'high', 'medium', 'low'
    High: 3+ stressed sessions in last 5
    Medium: 2 stressed sessions in last 5
    Low: otherwise
    """
    recent = memory.get("mood_history", [])[-5:]
    if len(recent) < 3:
        return "low"
    stressed_count = sum(1 for m in recent if m["mood"] == "stressed")
    if stressed_count >= 3:
        return "high"
    elif stressed_count == 2:
        return "medium"
    return "low"

def burnout_message(risk):
    if risk == "high":
        return "🚨 High burnout risk detected. ASK AI has noticed you've been stressed in most recent sessions. Please take care of yourself."
    elif risk == "medium":
        return "⚠️ Moderate stress pattern detected. You've had a few tough sessions. Check in with yourself today."
    return None

# ─── MEMORY SYSTEM ───────────────────────────────────────────────────────────

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
            # Migrate old single-goal format to multi-goal
            if "goal" in data and "goals" not in data:
                data["goals"] = [
                    {"category": "🚀 Startup", "text": data["goal"], "active": True}
                ] if data.get("goal") else []
            return data
    return {
        "name": None,
        "goals": [],
        "sessions": 0,
        "last_mood": "neutral",
        "last_seen": None,
        "conversation_history": [],
        "mood_history": [],
        "weekly_summary_shown": 0
    }

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def update_mood_history(memory, mood):
    memory["mood_history"].append({
        "mood": mood,
        "score": mood_to_score(mood),
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "session": memory.get("sessions", 0)
    })
    memory["mood_history"] = memory["mood_history"][-30:]

def get_active_goals(memory):
    return [g for g in memory.get("goals", []) if g.get("active", True)]

def should_show_weekly_summary(memory):
    sessions = memory.get("sessions", 0)
    last_summary = memory.get("weekly_summary_shown", 0)
    return sessions > 0 and sessions % 7 == 0 and sessions != last_summary

# ─── AI ENGINE ───────────────────────────────────────────────────────────────

def build_system_prompt(memory):
    name = memory.get("name", "the user")
    sessions = memory.get("sessions", 0)
    last_mood = memory.get("last_mood", "neutral")
    last_seen = memory.get("last_seen", "first time")
    active_goals = get_active_goals(memory)
    goals_text = "\n".join([f"  - {g['category']}: {g['text']}" for g in active_goals]) if active_goals else "  - No goals set yet"
    burnout_risk = check_burnout_risk(memory)

    mood_trend = ""
    if len(memory.get("mood_history", [])) >= 3:
        recent_moods = [m["mood"] for m in memory["mood_history"][-3:]]
        if recent_moods.count("stressed") >= 2:
            mood_trend = "IMPORTANT: The user has been stressed repeatedly. Be extra supportive. Gently acknowledge their stress before anything else."
        elif recent_moods.count("motivated") >= 2:
            mood_trend = "The user has been consistently motivated. Match their energy and help them push further."

    burnout_note = ""
    if burnout_risk == "high":
        burnout_note = "BURNOUT ALERT: This user is showing high burnout risk. Prioritize their wellbeing over productivity advice. Be gentle, warm, and caring."
    elif burnout_risk == "medium":
        burnout_note = "STRESS NOTE: Moderate stress pattern detected. Check in on how they are feeling before diving into tasks."

    return f"""You are ASK AI — a deeply personal AI companion built by A Square Innovations.

You are NOT a generic assistant. You are {name}'s personal AI. You know them, remember them, and genuinely care about their growth and wellbeing.

WHAT YOU KNOW ABOUT {name.upper()}:
- Name: {name}
- Active Goals:
{goals_text}
- Sessions together: {sessions}
- Last mood: {last_mood} {emotion_emoji(last_mood)}
- Last seen: {last_seen}
{mood_trend}
{burnout_note}

YOUR PERSONALITY:
- Warm, direct, honest — like a brilliant friend who genuinely cares
- Always reference their specific goals by name — never be generic
- When stressed: acknowledge feelings FIRST, then help
- When progress made: celebrate genuinely and specifically
- Ask one thoughtful follow-up question per response

YOUR RULES:
- Never forget the user's name or goals
- This is NOT a first meeting unless sessions = 0
- Keep responses to 3-5 sentences unless detailed help is needed
- Never say "As an AI" — you are ASK AI, their personal companion
- If multiple goals exist, occasionally ask which goal they want to focus on today
"""

def build_weekly_summary_prompt(memory):
    name = memory.get("name", "the user")
    sessions = memory.get("sessions", 0)
    active_goals = get_active_goals(memory)
    goals_text = ", ".join([f"{g['category']}: {g['text']}" for g in active_goals])
    recent = memory.get("mood_history", [])[-7:]
    stressed = sum(1 for m in recent if m["mood"] == "stressed")
    motivated = sum(1 for m in recent if m["mood"] == "motivated")
    neutral = sum(1 for m in recent if m["mood"] == "neutral")
    burnout_risk = check_burnout_risk(memory)

    return f"""You are ASK AI giving {name} their weekly summary after {sessions} total sessions.

Their active goals: {goals_text}
This week: {motivated} motivated sessions, {neutral} neutral, {stressed} stressed.
Burnout risk level: {burnout_risk}

Write a warm, honest weekly summary (5-7 sentences):
1. Acknowledge the emotional pattern of their week honestly
2. Comment on their progress across their goals specifically
3. If burnout risk is high or medium — address it directly with care
4. Highlight one thing to be proud of
5. Give one specific action for next week tied to their most important goal
6. End with a personal motivational message

Be honest, warm, specific. This is their weekly reflection from someone who truly knows them."""

def chat_with_askai(user_message, memory, api_key, prompt_override=None):
    client = Groq(api_key=api_key.strip())
    system = prompt_override if prompt_override else build_system_prompt(memory)
    messages = [{"role": "system", "content": system}]
    for msg in memory.get("conversation_history", [])[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=messages,
        max_tokens=500,
        temperature=0.85
    )
    return response.choices[0].message.content

# ─── MOOD CHART ──────────────────────────────────────────────────────────────

def render_mood_chart(memory):
    mood_history = memory.get("mood_history", [])
    if len(mood_history) < 2:
        st.caption("Chat more to see your mood chart.")
        return
    color_map = {"motivated": "#27AE60", "neutral": "#3498DB", "stressed": "#E74C3C"}
    recent = mood_history[-10:]
    bar_html = "<div style='display:flex;align-items:flex-end;gap:4px;height:80px;padding:4px 0'>"
    for entry in recent:
        height = int((entry["score"] / 3) * 70)
        color = color_map.get(entry["mood"], "#3498DB")
        label = f"S{entry.get('session','?')}"
        bar_html += f"""<div style='display:flex;flex-direction:column;align-items:center;flex:1'>
            <div style='width:100%;background:{color};height:{height}px;border-radius:4px 4px 0 0;min-height:8px'></div>
            <span style='font-size:9px;color:#888;margin-top:2px'>{label}</span></div>"""
    bar_html += "</div><div style='display:flex;gap:8px;margin-top:4px;font-size:11px'><span>🔥 Motivated</span><span>😊 Neutral</span><span>😟 Stressed</span></div>"
    st.markdown(bar_html, unsafe_allow_html=True)

# ─── STREAMLIT UI ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(page_title="ASK AI — A Square", page_icon="🧠", layout="centered")

    st.markdown("""
    <style>
    .stTextInput > div > div > input { border-radius: 12px; border: 2px solid #2E86C1; padding: 10px; }
    .stButton > button { background-color: #1B3A6B; color: white; border-radius: 12px; padding: 8px 24px; font-weight: bold; border: none; width: 100%; }
    .stButton > button:hover { background-color: #2E86C1; }
    .chat-message-user { background: #2E86C1; color: #FFFFFF; border-radius: 12px; padding: 12px 16px; margin: 8px 0; text-align: right; }
    .chat-message-ai { background: #1B3A6B; color: #FFFFFF; border-radius: 12px; padding: 12px 16px; margin: 8px 0; border-left: 4px solid #2E86C1; }
    .burnout-high { background: linear-gradient(135deg, #7B0000, #C0392B); color: white; border-radius: 12px; padding: 16px; margin: 12px 0; border-left: 4px solid #FF0000; }
    .burnout-medium { background: linear-gradient(135deg, #7B5E00, #D4AC0D); color: white; border-radius: 12px; padding: 16px; margin: 12px 0; border-left: 4px solid #F1C40F; }
    .weekly-summary { background: linear-gradient(135deg, #1B3A6B, #2E86C1); color: #FFFFFF; border-radius: 16px; padding: 20px; margin: 16px 0; }
    .goal-card { background: #1B3A6B; color: white; border-radius: 10px; padding: 10px 14px; margin: 4px 0; font-size: 13px; border-left: 3px solid #2E86C1; }
    </style>
    """, unsafe_allow_html=True)

    # ── Session state init ──
    for key, default in [
        ("memory", None), ("chat_started", False), ("current_mood", "neutral"),
        ("messages_display", []), ("show_weekly_summary", False),
        ("weekly_summary_text", ""), ("adding_goal", False)
    ]:
        if key not in st.session_state:
            st.session_state[key] = default if default is not None else (load_memory() if key == "memory" else default)

    if st.session_state.memory is None:
        st.session_state.memory = load_memory()

    memory = st.session_state.memory
    active_goals = get_active_goals(memory)
    burnout_risk = check_burnout_risk(memory)

    # ─── SIDEBAR ──────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🧠 ASK AI")
        st.markdown("*A Square Innovations — v0.3*")
        st.divider()

        if memory["name"]:
            st.markdown(f"**👤** {memory['name']}")
            st.markdown(f"**💬 Sessions:** {memory['sessions']}")
            st.markdown(f"**📅** {memory.get('last_seen', 'First time!')}")

            mood = st.session_state.current_mood
            mood_color = {"stressed": "#E74C3C", "motivated": "#27AE60", "neutral": "#3498DB"}.get(mood, "#3498DB")
            st.markdown(f"**Mood:** <span style='color:{mood_color};font-weight:bold'>{emotion_emoji(mood)} {mood.capitalize()}</span>", unsafe_allow_html=True)

            # Burnout indicator
            if burnout_risk == "high":
                st.markdown("🚨 <span style='color:#E74C3C;font-weight:bold'>High Burnout Risk</span>", unsafe_allow_html=True)
            elif burnout_risk == "medium":
                st.markdown("⚠️ <span style='color:#F1C40F;font-weight:bold'>Moderate Stress</span>", unsafe_allow_html=True)

            # Goals section
            st.divider()
            st.markdown("**🎯 Active Goals**")
            if active_goals:
                for i, goal in enumerate(active_goals):
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.markdown(f"<div class='goal-card'>{goal['category']}<br><small>{goal['text'][:45]}{'...' if len(goal['text']) > 45 else ''}</small></div>", unsafe_allow_html=True)
                    with col2:
                        if st.button("✕", key=f"del_goal_{i}"):
                            memory["goals"][i]["active"] = False
                            save_memory(memory)
                            st.session_state.memory = memory
                            st.rerun()
            else:
                st.caption("No active goals. Add one below.")

            if st.button("➕ Add Goal"):
                st.session_state.adding_goal = not st.session_state.adding_goal

            if st.session_state.adding_goal:
                with st.form("add_goal_form"):
                    cat = st.selectbox("Category", GOAL_CATEGORIES)
                    goal_text = st.text_input("Goal", placeholder="e.g. Launch beta by August")
                    if st.form_submit_button("Add →"):
                        if goal_text.strip():
                            if "goals" not in memory:
                                memory["goals"] = []
                            memory["goals"].append({"category": cat, "text": goal_text.strip(), "active": True})
                            save_memory(memory)
                            st.session_state.memory = memory
                            st.session_state.adding_goal = False
                            st.rerun()

            # Mood chart
            st.divider()
            st.markdown("**📊 Mood Dashboard**")
            render_mood_chart(memory)

            if len(memory.get("mood_history", [])) >= 3:
                recent = memory["mood_history"][-7:]
                motivated_count = sum(1 for m in recent if m["mood"] == "motivated")
                stressed_count = sum(1 for m in recent if m["mood"] == "stressed")
                st.markdown(f"""<div style='display:flex;gap:8px;margin-top:8px'>
                    <div style='flex:1;background:#1a3a1a;border-radius:8px;padding:8px;text-align:center'>
                        <div style='color:#27AE60;font-size:20px;font-weight:bold'>{motivated_count}</div>
                        <div style='color:#888;font-size:10px'>motivated</div></div>
                    <div style='flex:1;background:#3a1a1a;border-radius:8px;padding:8px;text-align:center'>
                        <div style='color:#E74C3C;font-size:20px;font-weight:bold'>{stressed_count}</div>
                        <div style='color:#888;font-size:10px'>stressed</div></div>
                </div>""", unsafe_allow_html=True)

            # Weekly summary button
            if memory.get("sessions", 0) >= 3:
                st.divider()
                if st.button("📋 Weekly Summary"):
                    active_key = st.session_state.get("saved_api_key", "")
                    if active_key:
                        with st.spinner("Generating your summary..."):
                            try:
                                summary = chat_with_askai(
                                    "Generate my weekly summary.",
                                    memory, active_key,
                                    prompt_override=build_weekly_summary_prompt(memory)
                                )
                                st.session_state.weekly_summary_text = summary
                                st.session_state.show_weekly_summary = True
                                memory["weekly_summary_shown"] = memory.get("sessions", 0)
                                save_memory(memory)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    else:
                        st.warning("Enter your API key first.")

        st.divider()
        api_key = st.text_input("🔑 Groq API Key", type="password", placeholder="gsk_...")
        if api_key:
            st.session_state.saved_api_key = api_key.strip()
        st.caption("Get free key at console.groq.com")

        if st.button("🔄 Reset Memory"):
            if os.path.exists(MEMORY_FILE):
                os.remove(MEMORY_FILE)
            for key in ["memory", "chat_started", "messages_display",
                        "current_mood", "show_weekly_summary", "weekly_summary_text", "adding_goal"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

    # ─── MAIN AREA ────────────────────────────────────────────
    st.markdown("# 🧠 ASK AI")
    st.markdown("*Your personal AI that remembers you, tracks your goals, and understands how you feel.*")
    st.divider()

    # ── BURNOUT ALERT (main area) ──
    if memory.get("name") and st.session_state.chat_started:
        msg = burnout_message(burnout_risk)
        if msg:
            css_class = "burnout-high" if burnout_risk == "high" else "burnout-medium"
            st.markdown(f'<div class="{css_class}">{msg}</div>', unsafe_allow_html=True)

    # ── WEEKLY SUMMARY ──
    if st.session_state.show_weekly_summary and st.session_state.weekly_summary_text:
        st.markdown(f"""<div class="weekly-summary">
            <h3>📋 Your Weekly Summary</h3>
            <p>{st.session_state.weekly_summary_text}</p>
        </div>""", unsafe_allow_html=True)
        if st.button("✅ Got it, continue chatting"):
            st.session_state.show_weekly_summary = False
            st.rerun()
        st.stop()

    # ── ONBOARDING ──
    if not memory["name"]:
        st.markdown("### 👋 Welcome! Let's set up your profile.")
        st.markdown("ASK AI will remember you, your goals, and how you feel — across every session.")

        with st.form("onboarding_form"):
            name_input = st.text_input("What's your name?", placeholder="e.g. Asmit")
            st.markdown("**What are your goals?** (Add at least one)")
            cat1 = st.selectbox("Goal 1 Category", GOAL_CATEGORIES, key="cat1")
            goal1 = st.text_input("Goal 1", placeholder="e.g. Build ASK AI and win MSME competition")
            cat2 = st.selectbox("Goal 2 Category (optional)", ["— Skip —"] + GOAL_CATEGORIES, key="cat2")
            goal2 = st.text_input("Goal 2 (optional)", placeholder="e.g. Stay consistent with fitness")

            submitted = st.form_submit_button("Start My Journey →")
            if submitted:
                if not name_input or not goal1:
                    st.error("Please enter your name and at least one goal.")
                elif not st.session_state.get("saved_api_key"):
                    st.error("Please enter your Groq API key in the sidebar first.")
                else:
                    goals = [{"category": cat1, "text": goal1.strip(), "active": True}]
                    if goal2.strip() and cat2 != "— Skip —":
                        goals.append({"category": cat2, "text": goal2.strip(), "active": True})

                    memory["name"] = name_input.strip()
                    memory["goals"] = goals
                    memory["sessions"] = 1
                    memory["last_seen"] = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
                    save_memory(memory)
                    st.session_state.memory = memory
                    st.session_state.chat_started = True

                    goals_str = " | ".join([f"{g['category']}: {g['text']}" for g in goals])
                    welcome = chat_with_askai(
                        f"Hi! I'm {name_input}. My goals are: {goals_str}. This is our first session.",
                        memory, st.session_state.saved_api_key
                    )
                    st.session_state.messages_display = [{"role": "assistant", "content": welcome}]
                    memory["conversation_history"].append({"role": "assistant", "content": welcome})
                    save_memory(memory)
                    st.rerun()

    # ── RETURNING USER ──
    elif not st.session_state.chat_started:
        sessions = memory.get("sessions", 0)
        last_mood = memory.get("last_mood", "neutral")
        st.markdown(f"### Welcome back, {memory['name']}! 👋")

        if active_goals:
            st.markdown("**Your active goals:**")
            for g in active_goals:
                st.markdown(f"<div class='goal-card'>{g['category']} — {g['text']}</div>", unsafe_allow_html=True)

        active_key = st.session_state.get("saved_api_key", "")
        if not active_key:
            st.warning("Enter your Groq API key in the sidebar to continue.")
        else:
            if st.button(f"Continue My Journey (Session {sessions + 1}) →"):
                memory["sessions"] = sessions + 1
                memory["last_seen"] = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
                save_memory(memory)
                st.session_state.chat_started = True

                if should_show_weekly_summary(memory):
                    with st.spinner("Preparing your weekly summary..."):
                        summary = chat_with_askai(
                            "Generate my weekly summary now.", memory, active_key,
                            prompt_override=build_weekly_summary_prompt(memory)
                        )
                        st.session_state.weekly_summary_text = summary
                        st.session_state.show_weekly_summary = True
                        memory["weekly_summary_shown"] = memory["sessions"]
                        save_memory(memory)
                        st.rerun()

                goals_str = " | ".join([f"{g['category']}: {g['text']}" for g in active_goals])
                returning_msg = f"Starting session {memory['sessions']}. Last mood: {last_mood}. Active goals: {goals_str}. Say hello, check in on how they are doing today, and ask which goal they want to focus on."
                welcome_back = chat_with_askai(returning_msg, memory, active_key)
                st.session_state.messages_display = [{"role": "assistant", "content": welcome_back}]
                memory["conversation_history"].append({"role": "assistant", "content": welcome_back})
                save_memory(memory)
                st.rerun()

    # ── CHAT ──
    else:
        active_key = st.session_state.get("saved_api_key", "")
        if not active_key:
            st.warning("⚠️ Enter your Groq API key in the sidebar to chat.")
            st.stop()

        for msg in st.session_state.messages_display:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-message-user">👤 <b>{memory["name"]}</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message-ai">🧠 <b>ASK AI</b><br>{msg["content"]}</div>', unsafe_allow_html=True)

        st.markdown("---")

        with st.form("chat_form", clear_on_submit=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                user_input = st.text_input("Talk to ASK AI", placeholder="How are you feeling? What's on your mind?", label_visibility="collapsed")
            with col2:
                send = st.form_submit_button("Send →")

        if send and user_input.strip():
            mood = detect_emotion(user_input)
            st.session_state.current_mood = mood
            memory["last_mood"] = mood
            update_mood_history(memory, mood)
            st.session_state.messages_display.append({"role": "user", "content": user_input})
            memory["conversation_history"].append({"role": "user", "content": user_input})

            with st.spinner("ASK AI is thinking..."):
                try:
                    response = chat_with_askai(user_input, memory, active_key)
                    st.session_state.messages_display.append({"role": "assistant", "content": response})
                    memory["conversation_history"].append({"role": "assistant", "content": response})
                    save_memory(memory)
                    st.session_state.memory = memory
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}. Check your API key in the sidebar.")

if __name__ == "__main__":
    main()
