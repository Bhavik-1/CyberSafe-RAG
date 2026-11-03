
import sys
import html
from pathlib import Path

import gradio as gr


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

import rag_pipeline as rag


# ============================================================
# 2. LOAD RAG MODELS ONCE
# ============================================================

print("\n" + "=" * 65)
print("STARTING CYBERSAFE RAG")
print("=" * 65)

if not rag.API_KEY:
    raise ValueError(
        "GEMINI_API_KEY missing from .env file."
    )

embedding_model, reranker = rag.load_models()

components = rag.prepare_retrieval(
    "fixed",
    embedding_model
)

client = rag.genai.Client(
    api_key=rag.API_KEY
)

print("\nCyberSafe RAG is ready!")


# ============================================================
# 3. CHAT FUNCTION
# ============================================================

def respond(message):

    if not message or not message.strip():
        return (
            "Please enter a cybersecurity question.",
            []
        )

    result = rag.run_query(
        message.strip(),
        components,
        reranker,
        client
    )

    answer = result.get(
        "answer",
        "No answer was generated."
    )

    evidence = result.get("results", [])

    evidence_cards = []

    for i, item in enumerate(evidence, start=1):

        evidence_cards.append({
            "number": i,
            "title": item.get("source_title", "Unknown source"),
            "issuer": item.get("issuer", "Unknown"),
            "page": item.get("page", "Unknown"),
            "score": item.get("cross_encoder_score", 0),
            "text": item.get("text", "")
        })

    return answer, evidence_cards


# ============================================================
# 4. EVIDENCE DISPLAY
# ============================================================

def display_evidence(evidence):

    if not evidence:
        return "<p class='empty-evidence'>No evidence retrieved yet.</p>"

    output = '<div class="evidence-list">'

    for item in evidence:

        title = html.escape(
            str(item.get("title", "Unknown source"))
        )

        issuer = html.escape(
            str(item.get("issuer", "Unknown"))
        )

        page = html.escape(
            str(item.get("page", "Unknown"))
        )

        source_text = html.escape(
            str(item.get("text", ""))
        )

        try:
            score = float(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0.0

        number = int(item.get("number", 0))

        output += f"""
        <details class="evidence-card">
            <summary>
                <div class="evidence-heading">

                    <span class="evidence-number">
                        {number:02d}
                    </span>

                    <div class="evidence-title">
                        <strong>{title}</strong>
                        <small>{issuer} · Page {page}</small>
                    </div>

                    <span class="evidence-score">
                        {score:.2f}
                    </span>

                </div>
            </summary>

            <div class="evidence-content">

                <div class="metadata-row">
                    <span>ISSUER</span>
                    <strong>{issuer}</strong>
                </div>

                <div class="metadata-row">
                    <span>PAGE</span>
                    <strong>{page}</strong>
                </div>

                <div class="metadata-row">
                    <span>RERANKER SCORE</span>
                    <strong>{score:.3f}</strong>
                </div>

                <hr>

                <div class="source-text">{source_text}</div>

            </div>
        </details>
        """

    output += "</div>"

    return output


# ============================================================
# 5. SUGGESTED QUESTIONS
# ============================================================

EXAMPLES = [
    "What should I do if I receive a phishing email?",
    "How can I protect my online accounts using MFA?",
    "How should passwords be stored securely?",
    "What should I do if my account is compromised?"
]


# ============================================================
# 6. CUSTOM CSS
# ============================================================

CUSTOM_CSS = """

/* GLOBAL */

.gradio-container {
    background: #080e1b !important;
    color: #e5edf8 !important;
    max-width: 1600px !important;
}

body {
    background: #080e1b !important;
}

/* HEADER */

#main-header {
    text-align: center;
    padding: 22px 10px 18px;
}

#main-header h1 {
    font-size: 38px;
    font-weight: 800;
    color: #f1f7ff;
    margin-bottom: 5px;
}

#main-header p {
    color: #91a4bd;
    font-size: 15px;
}

/* SIDEBAR */

#sidebar {
    background: #101a2c;
    border: 1px solid #253953;
    border-radius: 16px;
    padding: 18px;
}

/* CHAT PANEL */

#chat-panel {
    background: #101a2c;
    border: 1px solid #253953;
    border-radius: 16px;
    padding: 15px;
}

/* EVIDENCE PANEL */

#evidence-panel {
    background: #101a2c;
    border: 1px solid #253953;
    border-radius: 16px;
    padding: 15px;
}

/* EVIDENCE LIST */

.evidence-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
}

.evidence-card {
    background: #111e32;
    border: 1px solid #304660;
    border-radius: 10px;
    overflow: hidden;
}

.evidence-card summary {
    cursor: pointer;
    padding: 13px;
    list-style-position: inside;
}

.evidence-heading {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    width: calc(100% - 20px);
    vertical-align: middle;
}

.evidence-number {
    color: #43d9e8;
    font-size: 12px;
    font-weight: 800;
}

.evidence-title {
    display: flex;
    flex-direction: column;
    gap: 4px;
    flex: 1;
    min-width: 0;
}

.evidence-title strong {
    color: #e5edf8;
    font-size: 13px;
    overflow-wrap: anywhere;
}

.evidence-title small {
    color: #91a4bd;
    font-size: 11px;
}

.evidence-score {
    color: #43d9e8;
    font-size: 11px;
    white-space: nowrap;
}

.evidence-content {
    color: #c3d0e2;
    line-height: 1.65;
    padding: 12px 15px;
    border-top: 1px solid #304660;
    overflow-wrap: anywhere;
}

.metadata-row {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin: 8px 0;
    font-size: 12px;
}

.metadata-row span {
    color: #8298b5;
    font-size: 10px;
    font-weight: 700;
}

.metadata-row strong {
    color: #e5edf8;
    text-align: right;
}

.evidence-content hr {
    border-color: #304660;
    margin: 14px 0;
}

.source-text {
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font-size: 12px;
    line-height: 1.7;
    max-height: 280px;
    overflow-y: auto;
    padding: 12px;
    background: #0b1525;
    border-radius: 8px;
    color: #c3d0e2;
}

.empty-evidence {
    color: #91a4bd;
    font-size: 13px;
    padding: 15px 5px;
}

/* BUTTONS */

.gradio-container button.primary {
    background: #0789c7 !important;
    border-color: #0789c7 !important;
}

#clear-button {
    background: #253953 !important;
}

/* FOOTER */

#footer {
    text-align: center;
    color: #71839d;
    font-size: 12px;
    padding: 18px;
}

footer {
    display: none !important;
}

/* RESPONSIVE */

@media (max-width: 900px) {

    #main-header h1 {
        font-size: 28px;
    }

    #sidebar {
        margin-bottom: 12px;
    }

}

"""


# ============================================================
# 7. CHAT EVENT HANDLER
# ============================================================

def chat_response(message, history):

    if not message or not message.strip():

        return (
            "",
            history or [],
            [],
            "<p class='empty-evidence'>No evidence retrieved yet.</p>"
        )

    try:

        answer, evidence = respond(message)

        updated_history = list(history or [])

        updated_history.append({
            "role": "user",
            "content": message
        })

        updated_history.append({
            "role": "assistant",
            "content": answer
        })

        return (
            "",
            updated_history,
            evidence,
            display_evidence(evidence)
        )

    except Exception as error:

        print("\nApplication error:", error)

        return (
            "",
            list(history or []) + [
                {
                    "role": "assistant",
                    "content": (
                        "An error occurred while processing your question. "
                        "Please check the terminal."
                    )
                }
            ],
            [],
            "<p class='empty-evidence'>Evidence could not be displayed.</p>"
        )


# ============================================================
# 8. BUILD APPLICATION
# ============================================================

with gr.Blocks(
    title="CyberSafe RAG"
) as demo:

    gr.HTML("""
    <div id="main-header">
        <h1>🛡️ CyberSafe RAG</h1>
        <p>
            Evidence-grounded cybersecurity awareness
            and incident response assistant
        </p>
    </div>
    """)

    evidence_state = gr.State([])

    with gr.Row(equal_height=False):

        # ----------------------------------------------------
        # SIDEBAR
        # ----------------------------------------------------

        with gr.Column(
            scale=1,
            min_width=220,
            elem_id="sidebar"
        ):

            gr.Markdown("## 🛡️ CyberSafe")

            gr.Markdown(
                "Your AI-powered cybersecurity assistant, "
                "grounded in trusted security documents."
            )

            gr.Markdown("---")

            gr.Markdown("### ⚡ Suggested Questions")

            question_buttons = []

            for example in EXAMPLES:

                button = gr.Button(
                    example,
                    size="sm",
                    variant="secondary"
                )

                question_buttons.append(
                    (button, example)
                )

            gr.Markdown("---")

            gr.Markdown(
                """
### 📚 Knowledge Sources

- CERT-In
- NIST
- OWASP

---

### 🔒 Safety First

- Evidence-grounded responses
- Transparent source citations
- Abstention when evidence is insufficient
"""
            )

        # ----------------------------------------------------
        # CHAT COLUMN
        # ----------------------------------------------------

        with gr.Column(
            scale=2,
            min_width=350
        ):

            with gr.Group(elem_id="chat-panel"):

                gr.Markdown("## 💬 Assistant Response")

                chatbot = gr.Chatbot(
                    height=530,
                    placeholder="Ask CyberSafe a cybersecurity question..."
                )

                msg = gr.Textbox(
                    placeholder=(
                        "Ask about phishing, malware, passwords, "
                        "account security..."
                    ),
                    show_label=False,
                    lines=2
                )

                with gr.Row():

                    submit_btn = gr.Button(
                        "Send Message ➤",
                        variant="primary"
                    )

                    clear_btn = gr.Button(
                        "Clear Chat",
                        elem_id="clear-button"
                    )

        # ----------------------------------------------------
        # EVIDENCE COLUMN
        # ----------------------------------------------------

        with gr.Column(
            scale=1,
            min_width=300
        ):

            with gr.Group(elem_id="evidence-panel"):

                gr.Markdown("## 📖 Retrieved Evidence")

                gr.Markdown(
                    "Inspect the documents used to generate the answer."
                )

                evidence_html = gr.HTML(
                    value=(
                        "<p class='empty-evidence'>"
                        "No evidence retrieved yet."
                        "</p>"
                    )
                )

    # --------------------------------------------------------
    # FOOTER
    # --------------------------------------------------------

    gr.HTML("""
    <div id="footer">
        CyberSafe RAG • FAISS • BM25 • Cross-Encoder • Gemini
        <br>
        Knowledge sources: CERT-In, NIST and OWASP
    </div>
    """)

    # --------------------------------------------------------
    # SEND MESSAGE
    # --------------------------------------------------------

    submit_btn.click(
        fn=chat_response,
        inputs=[msg, chatbot],
        outputs=[
            msg,
            chatbot,
            evidence_state,
            evidence_html
        ]
    )

    # ENTER KEY
    msg.submit(
        fn=chat_response,
        inputs=[msg, chatbot],
        outputs=[
            msg,
            chatbot,
            evidence_state,
            evidence_html
        ]
    )

    # CLEAR CHAT
    clear_btn.click(
        fn=lambda: (
            "",
            [],
            [],
            "<p class='empty-evidence'>No evidence retrieved yet.</p>"
        ),
        inputs=None,
        outputs=[
            msg,
            chatbot,
            evidence_state,
            evidence_html
        ]
    )

    # SUGGESTED QUESTIONS
    for button, example in question_buttons:

        button.click(
            fn=lambda q=example: q,
            inputs=None,
            outputs=msg
        )


# ============================================================
# 9. LAUNCH
# ============================================================

if __name__ == "__main__":

    demo.queue()

    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        theme=gr.themes.Soft(
            primary_hue="cyan",
            secondary_hue="blue",
            neutral_hue="slate"
        ),
        css=CUSTOM_CSS,
        show_error=True
    )
