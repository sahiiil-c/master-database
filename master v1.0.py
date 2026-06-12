import streamlit as st
import os
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh

st_autorefresh(2000,limit=3)

# login imports 
from streamlit_oauth import OAuth2Component
import requests

# ── Page config ────────────────────────────────────────────────────────────────
file_name = os.path.basename(__file__)
st.set_page_config(page_title=file_name, layout="wide", page_icon="🔃")


# ── Firebase helpers ────────────────────────────────────────────────────────────

def start_app(path: dict, app_name: str):
    path = dict(path)
    path["private_key"] = path["private_key"].replace("\\n", "\n")
    try:
        app = firebase_admin.get_app(app_name)
    except ValueError:
        cred = credentials.Certificate(path)
        app = firebase_admin.initialize_app(cred, name=app_name)
    return firestore.client(app=app)


@st.cache_data(ttl=30, show_spinner=False)
def get_collections(_db) -> list[str]:
    return [col.id for col in _db.collections()]


@st.cache_data(ttl=30, show_spinner=False)
def get_documents(_db, col: str) -> list[str]:
    return [doc.id for doc in _db.collection(col).stream()]


def fetch_doc_data(_db, col: str, doc: str) -> dict:
    snapshot = _db.collection(col).document(doc).get()
    return snapshot.to_dict() or {}


def clear_cache():
    get_collections.clear()
    get_documents.clear()


def cast_value(val: str):
    v = val.strip()
    if v.lower() in ("none", "null", ""):
        return None
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if v.lstrip("-").isdigit() and v.count("-") <= 1:
        return int(v)
    try:
        return float(v)
    except ValueError:
        pass
    if v.startswith("[") and v.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(v)
            if isinstance(parsed, list):
                return [cast_value(str(i)) for i in parsed]
        except (ValueError, SyntaxError):
            pass
    return v


def save_field(_db, col, doc, top_key, sub_key, new_values):
    _db.collection(col).document(doc).update({f"{top_key}.{sub_key}": new_values})
# ─────────────────────────────────────────────
# Login Screen
# ─────────────────────────────────────────────
if not st.user.is_logged_in:
    st.title("🔐 Firebase Manager",text_alignment="center")
    st.markdown("<br><br>", unsafe_allow_html=True)

    if st.button("Log in with Google", use_container_width=True):
        st.login("google")

    st.stop()

# ─────────────────────────────────────────────
# Authorization Check
# ─────────────────────────────────────────────
allowed_users = st.secrets["mails"]

if st.user.email not in allowed_users:
    st.error("❌ You are not authorized to access this application.")

    if st.button("Logout", icon=":material/logout:"):
        st.logout()

    st.stop()

# ─────────────────────────────────────────────
# Session Timeout (10 minutes inactivity)
# ─────────────────────────────────────────────
import time

TIMEOUT_SECONDS = 10 * 60  # change this to whatever you want

if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()

# Check if timed out
if time.time() - st.session_state.last_active > TIMEOUT_SECONDS:
    st.session_state.clear()
    st.logout()
    st.stop()

# Reset timer on every interaction
st.session_state.last_active = time.time()

# ─────────────────────────────────────────────
# Cache Profile Picture
# ─────────────────────────────────────────────
if "profile_pic" not in st.session_state:

    profile_url = st.user.picture

    if profile_url:
        try:
            response = requests.get(profile_url, timeout=10)

            if response.status_code == 200:
                st.session_state.profile_pic = response.content
            else:
                st.session_state.profile_pic = None

        except Exception:
            st.session_state.profile_pic = None

    else:
        st.session_state.profile_pic = None

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
col1, col2, col3 = st.columns([1, 8, 1])

with col1:
    if st.session_state.profile_pic:
        st.image(st.session_state.profile_pic, width=60)
    else:
        st.image(
            "https://via.placeholder.com/60",
            width=60
        )

with col2:
    st.markdown(
        f"### 🔥 Firebase Manager — {st.user.name}"
    )

with col3:
    if st.button(
        "",
        icon=":material/logout:",
        use_container_width=True
    ):
        st.session_state.clear()
        st.logout()

st.divider()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("📂 Navigator")

    # ── App init ────────────────────────────────────────────────────────────────────

    try:
        types=['Ashus','Mayas']
        data=st.selectbox(f'Select Data from {types}',types,0)
        
        if st.session_state.get("previous_option") != data:
            st.session_state.previous_option = data
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
        if data == types[0]: 
            db = start_app(st.secrets["firebase1"], "db")
            collections = get_collections(db)
            col = st.selectbox(f"Collections ({len(collections)})", collections, index=min(1, len(collections) - 1),key="collections")
        else:
            db = start_app(st.secrets["firebase2"], "mdb")
            collections = get_collections(db)
            col = st.selectbox(f"Collections ({len(collections)})", collections, index=min(1, len(collections) - 1),key="collections")
    except Exception as e:
        st.error(f"❌ Firebase connection failed: {e}")
        st.stop()
    
    # collections = get_collections(db)
    if not collections:
        st.warning("No collections found.")
        st.stop()

    

    documents = get_documents(db, col)
    doc_display = {doc_id.capitalize(): doc_id for doc_id in documents}
    body_display = st.selectbox(f"Documents ({len(documents)})", list(doc_display.keys())) if documents else None
    body = doc_display[body_display] if body_display else None

    st.divider()

    # ── New Document ──────────────────────────────────────────────────────────
    st.subheader("➕ New Document")
    with st.form("new_doc_form"):
        new_doc_id = st.text_input("Document ID", placeholder="e.g. user_001")
        new_doc_raw = st.text_area(
            "Fields (one per line: key=value)",
            placeholder="name=John\nage=25\nactive=true",
            height=120,
        )
        if st.form_submit_button("Create Document", use_container_width=True):
            if not new_doc_id.strip():
                st.error("Document ID cannot be empty.")
            else:
                try:
                    new_data = {}
                    for line in new_doc_raw.strip().splitlines():
                        if "=" in line:
                            k, v = line.split("=", 1)
                            new_data[k.strip()] = cast_value(v.strip())
                    db.collection(col).document(new_doc_id.strip()).set(new_data)
                    clear_cache()
                    st.success(f"✅ `{new_doc_id}` created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

    st.divider()

    # ── Delete Document ───────────────────────────────────────────────────────
    if body:
        st.subheader("🗑️ Delete Document")
        confirm_del = st.checkbox(f"Confirm delete `{body}`")
        if st.button("Delete Document", type="primary", use_container_width=True, disabled=not confirm_del):
            try:
                db.collection(col).document(body).delete()
                clear_cache()
                st.success(f"🗑️ Deleted `{body}`")
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")

    st.divider()

    if st.button("🔄 Refresh", use_container_width=True):
        clear_cache()
        st.rerun()


# ── Main area ──────────────────────────────────────────────────────────────────

if not body:
    st.info("No documents found. Create one from the sidebar.")
    st.stop()

st.title(f"🔃 Firebase Editor — `{col}` / `{body}`")

doc_data = fetch_doc_data(db, col, body)

if not doc_data:
    st.info("Document is empty.")
    st.stop()

# ── Add new top-level field ────────────────────────────────────────────────────
with st.expander("➕ Add New Field to this Document"):
    with st.form("add_field_form"):
        new_field_key = st.text_input("Field name", placeholder="e.g. status")
        new_field_val = st.text_input("Value", placeholder="e.g. active / 42 / true / [1,2,3]")
        if st.form_submit_button("Add Field"):
            if not new_field_key.strip():
                st.error("Field name cannot be empty.")
            elif new_field_key in doc_data:
                st.error(f"`{new_field_key}` already exists. Edit it in the tab below.")
            else:
                try:
                    db.collection(col).document(body).update({new_field_key: cast_value(new_field_val)})
                    clear_cache()
                    st.success(f"✅ Field `{new_field_key}` added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed: {e}")

st.divider()

# ── Tabs per top-level field ───────────────────────────────────────────────────
key_list = list(doc_data.keys())
tabs = st.tabs([k.capitalize() for k in key_list])

for tab, top_key in zip(tabs, key_list):
    with tab:
        field_value = doc_data.get(top_key)

        

        # ── Case 1: dict ──────────────────────────────────────────────────────
        if isinstance(field_value, dict):
            if not field_value:
                st.info("Empty dict.")
            else:
                cols = st.columns(len(field_value))
                for column, sub_key in zip(cols, field_value.keys()):
                    with column:
                        st.markdown(f"**{sub_key}**")
                        sub_value = field_value[sub_key]
                        if not isinstance(sub_value, list):
                            sub_value = [sub_value]
                        with st.form(key=f"form_{body}_{top_key}_{sub_key}"):
                            inputs = []
                            for idx, item in enumerate(sub_value):
                                val = st.text_input(f"[{idx}]", value=str(item), key=f"ti_{body}_{top_key}_{sub_key}_{idx}")
                                inputs.append(cast_value(val))
                            if st.form_submit_button("💾 Save"):
                                try:
                                    save_field(db, col, body, top_key, sub_key, inputs)
                                    clear_cache()
                                    st.success("Saved!")
                                except Exception as e:
                                    st.error(f"Save failed: {e}")

            
                                
            # Append to sub-key (only shows if sub-key holds a list)
            list_subkeys = [sk for sk, sv in field_value.items() if isinstance(sv, list)]
            if list_subkeys:
                with st.expander(f"➕ Append item to sub-key in `{top_key}`"):
                    with st.form(f"append_subkey_{top_key}"):
                        sk_to_append = st.selectbox("Sub-key (list type only)", list_subkeys)
                        new_item = st.text_input("New value")
                        if st.form_submit_button("Append"):
                            try:
                                db.collection(col).document(body).update(
                                    {f"{top_key}.{sk_to_append}": firestore.ArrayUnion([cast_value(new_item)])}
                                )
                                clear_cache()
                                st.success(f"✅ Item appended to `{top_key}.{sk_to_append}`!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
                                
            # Remove item from a sub-key list
            list_subkeys = [sk for sk, sv in field_value.items() if isinstance(sv, list) and sv]
            if list_subkeys:
                with st.expander(f"🗑️ Remove item from sub-key list in `{top_key}`"):
                    with st.form(f"remove_subkey_item_{top_key}"):
                        sk_to_remove = st.selectbox("Sub-key (list type only)", list_subkeys, key=f"sk_rem_{top_key}")
                        items_in_sk = [str(i) for i in field_value[sk_to_remove]]
                        item_to_del = st.selectbox("Item to remove", items_in_sk, key=f"item_rem_{top_key}")
                        if st.form_submit_button("Remove"):
                            try:
                                db.collection(col).document(body).update(
                                    {f"{top_key}.{sk_to_remove}": firestore.ArrayRemove([cast_value(item_to_del)])}
                                )
                                clear_cache()
                                st.success(f"🗑️ Item removed from `{top_key}.{sk_to_remove}`!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
            
            # Add sub-key
            with st.expander(f"➕ Add sub-key to `{top_key}`"):
                with st.form(f"add_subkey_{top_key}"):
                    sk = st.text_input("Sub-key name")
                    sv = st.text_input("Value")
                    if st.form_submit_button("Add"):
                        if not sk.strip():
                            st.error("Sub-key cannot be empty.")
                        elif isinstance(field_value, dict) and sk in field_value:
                            st.error("Sub-key already exists.")
                        else:
                            try:
                                db.collection(col).document(body).update({f"{top_key}.{sk}": cast_value(sv)})
                                clear_cache()
                                st.success(f"✅ `{top_key}.{sk}` added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
            
            # Delete sub-key
            if isinstance(field_value, dict) and field_value:
                with st.expander(f"🗑️ Delete sub-key from `{top_key}`"):
                    with st.form(f"del_subkey_{top_key}"):
                        sk_to_del = st.selectbox("Sub-key to delete", list(field_value.keys()))
                        confirmed = st.checkbox("Confirm deletion")
                        if st.form_submit_button("Delete") and confirmed:
                            try:
                                db.collection(col).document(body).update({f"{top_key}.{sk_to_del}": firestore.DELETE_FIELD})
                                clear_cache()
                                st.success(f"🗑️ `{top_key}.{sk_to_del}` deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
            
            # Delete field button
            with st.expander(":warning: Delete the whole field"):
                with st.expander(":warning: Are you sure?"):
                    if st.button(f":warning: Delete field `{top_key}`", key=f"del_field_{top_key}"):
                        try:
                            db.collection(col).document(body).update({top_key: firestore.DELETE_FIELD})
                            clear_cache()
                            st.success(f"Field `{top_key}` deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

        # ── Case 2: list ──────────────────────────────────────────────────────
        elif isinstance(field_value, list):
            with st.form(key=f"form_{body}_{top_key}_list"):
                inputs = []
                for idx, item in enumerate(field_value):
                    val = st.text_input(f"[{idx}]", value=str(item), key=f"ti_{body}_{top_key}_list_{idx}")
                    inputs.append(cast_value(val))
                if st.form_submit_button("💾 Save Changes"):
                    try:
                        db.collection(col).document(body).update({top_key: inputs})
                        clear_cache()
                        st.success("Saved!")
                    except Exception as e:
                        st.error(f"Save failed: {e}")

            # Append to list
            with st.expander(f"➕ Append item to `{top_key}`"):
                with st.form(f"append_{top_key}"):
                    new_item = st.text_input("New value")
                    if st.form_submit_button("Append"):
                        try:
                            db.collection(col).document(body).update(
                                {top_key: firestore.ArrayUnion([cast_value(new_item)])}
                            )
                            clear_cache()
                            st.success("✅ Item appended!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

            # Remove from list
            if field_value:
                with st.expander(f"🗑️ Remove item from `{top_key}`"):
                    with st.form(f"remove_{top_key}"):
                        item_to_del = st.selectbox("Item to remove", [str(i) for i in field_value])
                        if st.form_submit_button("Remove"):
                            try:
                                db.collection(col).document(body).update(
                                    {top_key: firestore.ArrayRemove([cast_value(item_to_del)])}
                                )
                                clear_cache()
                                st.success("🗑️ Item removed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

        # ── Case 3: scalar ────────────────────────────────────────────────────
        else:
            with st.form(key=f"form_{body}_{top_key}_scalar"):
                val = st.text_input(top_key, value=str(field_value) if field_value is not None else "")
                if st.form_submit_button("💾 Save Changes"):
                    try:
                        db.collection(col).document(body).update({top_key: cast_value(val)})
                        clear_cache()
                        st.success("Saved!")
                    except Exception as e:
                        st.error(f"Save failed: {e}")
