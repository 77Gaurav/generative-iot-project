import requests
import streamlit as st

API_URL = "http://localhost:8000/query"

EXAMPLE_QUERY = (
    "We are building a weather monitoring IoT project to measure humidity, "
    "temperature, rainfall and wind speed, and display the readings on a small screen."
)

st.set_page_config(
    page_title="Generative IoT Project",
    page_icon="🌦️",
    layout="centered",
)

st.title("🌦️ Generative IoT Project Builder")
st.caption("Describe an IoT project and get the list of components you need.")

with st.form("query_form"):
    query = st.text_area(
        "What are we building?",
        value=EXAMPLE_QUERY,
        height=120,
        help="Describe your IoT project's goals in plain language.",
    )
    submitted = st.form_submit_button("Build the component list", type="primary")

if submitted:
    if not query.strip():
        st.warning("Please describe the project first.")
        st.stop()

    with st.spinner("Extracting requirements, retrieving components and validating the system..."):
        try:
            response = requests.post(API_URL, json={"q": query.strip()}, timeout=120)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.ConnectionError:
            st.error(
                "Could not reach the FastAPI backend at "
                f"{API_URL}. Start it with: "
                "`.venv/bin/uvicorn app.main:app --reload`"
            )
            st.stop()
        except Exception as exc:  # pragma: no cover - defensive
            st.error(f"Request failed: {exc}")
            st.stop()

    if not data.get("components"):
        st.warning("No components could be assembled for this project.")
    else:
        st.success(f"System is buildable: {data['answer']}")

        st.subheader("Components needed")
        for component in data["components"]:
            status_icon = "✅" if component.get("compatible") else "⚠️"
            with st.container(border=True):
                st.markdown(
                    f"**{status_icon} {component['name']}** "
                    f"`{component.get('role', '')}`"
                )
                st.caption(component.get("reason", ""))

        st.subheader("Compatibility checks")
        for check in data.get("checks", []):
            icon = "✅" if check.get("result") == "pass" else "❌"
            st.markdown(
                f"- {icon} **{check.get('type', '')}**: {check.get('reason', '')}"
            )

        if data.get("missing_requirements"):
            st.warning(
                "Missing requirements: " + ", ".join(data["missing_requirements"])
            )

        confidence = data.get("confidence")
        if confidence is not None:
            st.progress(float(confidence), text=f"Confidence: {confidence}")

    with st.expander("Detailed plan (requirements & sources)"):
        st.markdown("**Modified query (requirements)**")
        st.json(data.get("requirements"))
        st.markdown("**Thought process**")
        st.write(data.get("thought_process"))
        st.markdown("**Retrieved component candidates**")
        st.json(data.get("sources", [])[:5])