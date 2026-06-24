# 🔥 Firebase Database Manager — Multi-Role Admin Panel

A full-featured **Firebase Firestore management web app** built with Python and Streamlit, featuring **Google OAuth 2.0 authentication** and **role-based access control** (Admin & Client).

---

## 🚀 Features

- 🔐 **Google OAuth 2.0 Login** — Secure authentication via Google
- 👥 **Multi-Role Access Control**
  - **Admin** — Full CRUD access across all collections
  - **Client** — Read-only access scoped by secrets config
- 📁 **Collection & Document Management**
  - Browse collections and documents interactively
  - Create and delete documents
  - Add, edit, and delete fields
  - Manage nested subcollections
- 📋 **List Field Operations**
  - Append items using Firestore `ArrayUnion`
  - Remove items using Firestore `ArrayRemove`
  - No accidental overwrites
- 🔢 **Type-Safe Value Casting**
  - Preserves Firestore data types: `string`, `int`, `float`, `bool`, `list`
- 🧠 **Session & State Management**
  - Stable multi-user experience with caching controls
  - Form state handling to prevent accidental resubmission
- 🎨 **Clean UI**
  - Hidden Streamlit header for a native app feel
  - Sidebar toggle fully preserved

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python | Core language |
| Streamlit | Web UI framework |
| Firebase Firestore | NoSQL cloud database |
| Google OAuth 2.0 | Authentication |
| TOML Secrets Config | Role & credential management |

---

## 📂 Project Structure

```
master-database/
│
├── app.py                  # Main Streamlit application
├── secrets.toml            # Firebase & OAuth credentials (not pushed)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/sahiiil-c/master-database.git
cd master-database
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Secrets

Create a `.streamlit/secrets.toml` file with the following structure:

```toml
[google_oauth]
client_id = "YOUR_GOOGLE_CLIENT_ID"
client_secret = "YOUR_GOOGLE_CLIENT_SECRET"
redirect_uri = "http://localhost:8501"

[firebase]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key = "YOUR_PRIVATE_KEY"
client_email = "YOUR_CLIENT_EMAIL"

[roles]
admins = ["admin@example.com"]
clients = ["client@example.com"]
```

### 4. Run the App
```bash
streamlit run app.py
```

---

## 🔒 Authentication Flow

```
User visits app
      ↓
Google OAuth Login
      ↓
Email matched against secrets.toml
      ↓
Admin → Full CRUD Access
Client → Read-Only Scoped Access
Unknown → Access Denied
```

---

## 📸 Screenshots

> *(Add screenshots of your app UI here)*

---

## 🙋‍♂️ Author

**Sahil Gulab Chavan**
- 🎓 B.Tech AI & ML — Dilkap Research Institute (2027)
- 💼 Data Scientist Intern — Evoastra Ventures
- 🔗 [LinkedIn](https://www.linkedin.com/in/) | [GitHub](https://github.com/sahiiil-c)

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
