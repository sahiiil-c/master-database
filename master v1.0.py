import ast
import time


import requests
import streamlit as st
from firebase_admin import credentials, firestore
import firebase_admin
from streamlit_autorefresh import st_autorefresh

hide_st_style = """
            <style>
            MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            # [data-testid="stToolbar"] {
            #     visibility: hidden;
            #     height: 0%;
            # }
            [data-testid="stDecoration"] {
                visibility: hidden;
                height: 0%;
            }
            [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0%;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ── Page config ────────────────────────────────────────────────────────────────
# file_name = st.secrets.file_name
st.set_page_config(page_title=st.secrets.file_name, layout="wide", page_icon="☁")


# ── Firebase helpers ───────────────────────────────────────────────────────────

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


@st.cache_data(ttl=30, show_spinner=False)
def fetch_doc_data(_db, col: str, doc: str) -> dict:
    snapshot = _db.collection(col).document(doc).get()
    return snapshot.to_dict() or {}


def clear_cache():
    get_collections.clear()
    get_documents.clear()
    fetch_doc_data.clear()


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
            parsed = ast.literal_eval(v)
            if isinstance(parsed, list):
                return [cast_value(str(i)) for i in parsed]
        except (ValueError, SyntaxError):
            pass
    return v


def save_field(_db, col, doc, top_key, sub_key, new_values):
    _db.collection(col).document(doc).update({f"{top_key}.{sub_key}": new_values})


# ── Role resolution ────────────────────────────────────────────────────────────
# Dynamically discovers all firebase{num} keys from secrets.
# Admin  : email in st.secrets["emails"]
# Client : email in st.secrets["firebase{num}"]["allowed_emails"]
#          → gets access to that firebase only, and only to
#            st.secrets["firebase{num}"]["allowed_collections"]

def resolve_user_role(email: str):
    """
    Returns:
        ("admin", None, None)
        ("client", db_key: str, allowed_collections: list[str])
        ("unauthorized", None, None)
    """
    # Check admin list
    admin_emails = list(st.secrets.get("mails", []))
    if email in admin_emails:
        return ("admin", None, None)

    # Scan firebase1, firebase2, ... for a matching allowed_emails entry
    idx = 1
    while True:
        key = f"firebase{idx}"
        if key not in st.secrets:
            break
        fb_secret = st.secrets[key]
        allowed = list(fb_secret.get("allowed_emails", []))
        if email in allowed:
            allowed_cols = list(fb_secret.get("allowed_collections", []))
            return ("client", key, allowed_cols)
        idx += 1

    return ("unauthorized", None, None)


def discover_firebase_keys() -> list[str]:
    """Return all firebase{num} keys found in secrets, in order."""
    keys = []
    idx = 1
    while True:
        key = f"firebase{idx}"
        if key not in st.secrets:
            break
        keys.append(key)
        idx += 1
    return keys


# ── Login Screen ───────────────────────────────────────────────────────────────
if not st.user.is_logged_in:
    st.title("🔐 Firebase Manager",text_alignment="center")
    st.markdown("<br><br><br><br><br><br>", unsafe_allow_html=True)
    if st.button(":material/account_circle:  Log in with Google", use_container_width=True,):
        st.login("google")
    st.stop()

# ── Authorization & Role Check ─────────────────────────────────────────────────
role, client_db_key, client_allowed_cols = resolve_user_role(st.user.email)

if role == "unauthorized":
    st.error("❌ You must be authorized to access this application.")
    if st.button("Logout", icon=":material/logout:"):
        st.logout()
        st.rerun()
        
    st.stop()

# ── Auto-refresh (authenticated users only) ────────────────────────────────────
st_autorefresh(2000, limit=3, key="autorefresh")

# ── Session Timeout (10 minutes genuine inactivity) ───────────────────────────
TIMEOUT_SECONDS = 10 * 60

if "last_active" not in st.session_state:
    st.session_state.last_active = time.time()

if time.time() - st.session_state.last_active > TIMEOUT_SECONDS:
    st.session_state.clear()
    st.logout()
    st.rerun()
    st.stop()

is_autorefresh = st.query_params.get("autorefresh") is not None
if not is_autorefresh:
    st.session_state.last_active = time.time()

# ── Cache Profile Picture ──────────────────────────────────────────────────────
if "profile_pic" not in st.session_state:
    profile_url = st.user.picture
    if profile_url:
        try:
            response = requests.get(profile_url, timeout=10)
            st.session_state.profile_pic = (
                response.content if response.status_code == 200 else None
            )
        except Exception:
            st.session_state.profile_pic = None
    else:
        st.session_state.profile_pic = None

# ── Header ─────────────────────────────────────────────────────────────────────
hcol1, hcol2, hcol3 = st.columns([1, 8, 1])

with hcol1:
    if st.session_state.profile_pic:
        st.image(st.session_state.profile_pic, width=60)
    else:
        placeholder_svg = (
            "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
            "width='60' height='60'%3E%3Crect width='60' height='60' rx='30' "
            "fill='%23888'/%3E%3Ctext x='50%25' y='55%25' dominant-baseline='middle' "
            "text-anchor='middle' font-size='24' fill='white'%3E%3F%3C/text%3E%3C/svg%3E"
        )
        st.image(placeholder_svg, width=60)

with hcol2:
    role_badge = "🛡️ Admin" if role == "admin" else "👤 Client"
    st.markdown(f"### 🔥 Firebase Manager — {st.user.name}  `{role_badge}`")

with hcol3:
    if st.button("", icon=":material/logout:", use_container_width=True):
        st.session_state.clear()
        st.logout()
        st.rerun()

st.divider()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Navigator
# Admin  : sees Data selectbox (all firebase{num} keys) + Collections selectbox
# Client : no Data or Collections selectbox — locked to their assigned firebase
#          and only their allowed_collections
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.header("📂 Navigator")

    try:
        if role == "admin":
            # ── Admin: dynamic firebase selector ──────────────────────────────
            fb_keys = discover_firebase_keys()

            # Build display labels: use the key name itself (firebase1, firebase2…)
            # Admins can optionally set a "label" field inside each firebase secret
            # for a friendlier name, e.g. label = "Ashus"
            fb_labels = []
            for k in fb_keys:
                lbl = st.secrets[k].get("label", k)
                fb_labels.append(lbl)

            selected_label = st.selectbox(
                f"Select Database ({len(fb_keys)} found)",
                fb_labels,
                key="admin_db_select",
            )
            selected_fb_key = fb_keys[fb_labels.index(selected_label)]

            # Clear cache when the admin switches database
            if st.session_state.get("prev_fb_key") != selected_fb_key:
                st.session_state.prev_fb_key = selected_fb_key
                clear_cache()
                st.rerun()

            db = start_app(st.secrets[selected_fb_key], selected_fb_key)

            # Admin sees ALL collections
            all_collections = get_collections(db)
            if not all_collections:
                st.warning("No collections found in this database.")
                st.stop()

            col = st.selectbox(
                f"Collection ({len(all_collections)})",
                all_collections,
                index=min(1, len(all_collections) - 1),
                key="admin_col_select",
            )

        else:
            # ── Client: locked to their firebase + allowed_collections ─────────
            db = start_app(st.secrets[client_db_key], client_db_key)

            if not client_allowed_cols:
                st.warning("No collections have been assigned to your account.")
                st.stop()

            # Show collection selectbox only if they have more than one
            if len(client_allowed_cols) == 1:
                col = client_allowed_cols[0]
                st.info(f"📁 Collection: **{col}**")
            else:
                col = st.selectbox(
                    f"Collection ({len(client_allowed_cols)})",
                    client_allowed_cols,
                    key="client_col_select",
                )

    except Exception as e:
        st.error(f"❌ Firebase connection failed: {e}")
        st.stop()

    # ── Document selector (available to both roles) ────────────────────────────
    documents = get_documents(db, col)
    doc_display = {doc_id.capitalize(): doc_id for doc_id in documents}
    body_display = (
        st.selectbox(f"Document ({len(documents)})", list(doc_display.keys()))
        if documents
        else None
    )
    body = doc_display[body_display] if body_display else None

    st.divider()

    # ── New Document (both roles) ──────────────────────────────────────────────
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

    # ── Delete Document (both roles) ───────────────────────────────────────────
    if body:
        st.subheader("🗑️ Delete Document")
        confirm_del = st.checkbox(f"Confirm delete `{body}`")
        if st.button(
            "Delete Document",
            type="primary",
            use_container_width=True,
            disabled=not confirm_del,
        ):
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


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA — Editor
# ══════════════════════════════════════════════════════════════════════════════

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
        new_field_val = st.text_input(
            "Value", placeholder="e.g. active / 42 / true / [1,2,3]"
        )
        if st.form_submit_button("Add Field"):
            if not new_field_key.strip():
                st.error("Field name cannot be empty.")
            elif new_field_key in doc_data:
                st.error(f"`{new_field_key}` already exists. Edit it in the tab below.")
            else:
                try:
                    db.collection(col).document(body).update(
                        {new_field_key: cast_value(new_field_val)}
                    )
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

        # ── Case 1: dict ───────────────────────────────────────────────────────
        if isinstance(field_value, dict):
            if not field_value:
                st.info("Empty dict.")
            else:
                cols = st.columns(len(field_value))
                for column, sub_key in zip(cols, field_value.keys()):
                    with column:
                        st.markdown(f"**{sub_key}**")
                        sub_value = field_value[sub_key]
                        is_list_val = isinstance(sub_value, list)
                        with st.form(key=f"form_{body}_{top_key}_{sub_key}"):
                            if is_list_val:
                                # List sub-key: show indexed inputs, save as list
                                inputs = []
                                for idx, item in enumerate(sub_value):
                                    val = st.text_input(
                                        f"[{idx}]",
                                        value=str(item),
                                        key=f"ti_{body}_{top_key}_{sub_key}_{idx}",
                                    )
                                    inputs.append(cast_value(val))
                                if st.form_submit_button("💾 Save"):
                                    try:
                                        save_field(db, col, body, top_key, sub_key, inputs)
                                        clear_cache()
                                        st.success("Saved!")
                                    except Exception as e:
                                        st.error(f"Save failed: {e}")
                            else:
                                # Scalar sub-key: single input, save as scalar
                                val = st.text_input(
                                    "value",
                                    value=str(sub_value) if sub_value is not None else "",
                                    key=f"ti_{body}_{top_key}_{sub_key}_scalar",
                                )
                                if st.form_submit_button("💾 Save"):
                                    try:
                                        save_field(db, col, body, top_key, sub_key, cast_value(val))
                                        clear_cache()
                                        st.success("Saved!")
                                    except Exception as e:
                                        st.error(f"Save failed: {e}")

            # All sub-keys are eligible for append/remove.
            # Scalar sub-keys are treated as a 1-item list on append —
            # the first append converts them to a proper list in Firestore.
            list_subkeys_all = list(field_value.keys())
            list_subkeys_nonempty = [
                sk for sk, sv in field_value.items()
                if (isinstance(sv, list) and sv) or (not isinstance(sv, list) and sv is not None)
            ]

            if list_subkeys_all:
                with st.expander(f"➕ Append item to sub-key in `{top_key}`"):
                    with st.form(f"append_subkey_{top_key}"):
                        sk_to_append = st.selectbox(
                            "Sub-key (list type only)", list_subkeys_all
                        )
                        new_item = st.text_input("New value")
                        if st.form_submit_button("Append"):
                            try:
                                # Direct list append instead of ArrayUnion so
                                # duplicate values are allowed.
                                existing = field_value.get(sk_to_append)
                                if isinstance(existing, list):
                                    current_list = list(existing)
                                elif existing is None:
                                    current_list = []
                                else:
                                    # Scalar sub-key — promote to list on first append
                                    current_list = [existing]
                                current_list.append(cast_value(new_item))
                                db.collection(col).document(body).update(
                                    {f"{top_key}.{sk_to_append}": current_list}
                                )
                                clear_cache()
                                st.success(
                                    f"✅ Item appended to `{top_key}.{sk_to_append}`!"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

            if list_subkeys_nonempty:
                with st.expander(f"🗑️ Remove item from sub-key list in `{top_key}`"):
                    # sk_to_remove is outside the form so switching sub-key
                    # immediately refreshes the item list below.
                    sk_to_remove = st.selectbox(
                        "Sub-key (list type only)",
                        list_subkeys_nonempty,
                        key=f"sk_rem_{top_key}",
                    )
                    _raw = field_value[sk_to_remove]
                    current_items = _raw if isinstance(_raw, list) else [_raw]
                    item_labels = [f"{i}: {v}" for i, v in enumerate(current_items)]

                    with st.form(f"remove_subkey_item_{top_key}"):
                        selected_label = st.selectbox(
                            "Item to remove",
                            item_labels,
                            index=len(item_labels) - 1,
                            key=f"item_rem_{top_key}",
                        )
                        if st.form_submit_button("Remove"):
                            try:
                                selected_idx = int(selected_label.split(":")[0])
                                original_value = current_items[selected_idx]
                                db.collection(col).document(body).update(
                                    {
                                        f"{top_key}.{sk_to_remove}": firestore.ArrayRemove(
                                            [original_value]
                                        )
                                    }
                                )
                                clear_cache()
                                st.success(
                                    f"🗑️ Item removed from `{top_key}.{sk_to_remove}`!"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

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
                                db.collection(col).document(body).update(
                                    {f"{top_key}.{sk}": cast_value(sv)}
                                )
                                clear_cache()
                                st.success(f"✅ `{top_key}.{sk}` added!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

            if isinstance(field_value, dict) and field_value:
                with st.expander(f"🗑️ Delete sub-key from `{top_key}`"):
                    with st.form(f"del_subkey_{top_key}"):
                        sk_to_del = st.selectbox(
                            "Sub-key to delete", list(field_value.keys())
                        )
                        confirmed = st.checkbox("Confirm deletion")
                        if st.form_submit_button("Delete") and confirmed:
                            try:
                                db.collection(col).document(body).update(
                                    {f"{top_key}.{sk_to_del}": firestore.DELETE_FIELD}
                                )
                                clear_cache()
                                st.success(f"🗑️ `{top_key}.{sk_to_del}` deleted!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

            with st.expander(":warning: Delete the whole 
            Section"):
                with st.expander(":warning: Are you sure?"):
                    if st.button(
                        f":warning: Delete field `{top_key}`",
                        key=f"del_field_{top_key}",
                    ):
                        try:
                            db.collection(col).document(body).update(
                                {top_key: firestore.DELETE_FIELD}
                            )
                            clear_cache()
                            st.success(f"Field `{top_key}` deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

        # ── Case 2: list ───────────────────────────────────────────────────────
        elif isinstance(field_value, list):
            with st.form(key=f"form_{body}_{top_key}_list"):
                inputs = []
                for idx, item in enumerate(field_value):
                    val = st.text_input(
                        f"[{idx}]",
                        value=str(item),
                        key=f"ti_{body}_{top_key}_list_{idx}",
                    )
                    inputs.append(cast_value(val))
                if st.form_submit_button("💾 Save Changes"):
                    try:
                        db.collection(col).document(body).update({top_key: inputs})
                        clear_cache()
                        st.success("Saved!")
                    except Exception as e:
                        st.error(f"Save failed: {e}")

            with st.expander(f"➕ Append item to `{top_key}`"):
                with st.form(f"append_{top_key}"):
                    new_item = st.text_input("New value")
                    if st.form_submit_button("Append"):
                        try:
                            # Direct list append instead of ArrayUnion so
                            # duplicate values are allowed.
                            current_list = list(field_value)
                            current_list.append(cast_value(new_item))
                            db.collection(col).document(body).update(
                                {top_key: current_list}
                            )
                            clear_cache()
                            st.success("✅ Item appended!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")

            if field_value:
                with st.expander(f"🗑️ Remove item from `{top_key}`"):
                    with st.form(f"remove_{top_key}"):
                        item_labels = [f"{i}: {v}" for i, v in enumerate(field_value)]
                        selected_label = st.selectbox(
                            "Item to remove",
                            item_labels,
                            index=len(item_labels) - 1,
                        )
                        if st.form_submit_button("Remove"):
                            try:
                                selected_idx = int(selected_label.split(":")[0])
                                original_value = field_value[selected_idx]
                                db.collection(col).document(body).update(
                                    {top_key: firestore.ArrayRemove([original_value])}
                                )
                                clear_cache()
                                st.success("🗑️ Item removed!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")

        # ── Case 3: scalar ─────────────────────────────────────────────────────
        else:
            with st.form(key=f"form_{body}_{top_key}_scalar"):
                val = st.text_input(
                    top_key,
                    value=str(field_value) if field_value is not None else "",
                )
                if st.form_submit_button("💾 Save Changes"):
                    try:
                        db.collection(col).document(body).update(
                            {top_key: cast_value(val)}
                        )
                        clear_cache()
                        st.success("Saved!")
                    except Exception as e:
                        st.error(f"Save failed: {e}")
