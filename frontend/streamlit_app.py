import base64
import json
import os
import pickle
import time
from datetime import datetime
from urllib.parse import quote_plus

import requests
import streamlit as st

API_URL = "http://localhost:8000/chat"
STREAM_API_URL = "http://localhost:8000/chat_stream"
UPLOAD_URL = "http://localhost:8000/upload_pdfs"
RESET_URL = "http://localhost:8000/reset_memory"
CLEAR_KB_URL = "http://localhost:8000/clear_knowledge_base"
LIST_DOCS_URL = "http://localhost:8000/list_documents"
DELETE_DOC_URL = "http://localhost:8000/delete_document"
CLEAR_HISTORY_URL = "http://localhost:8000/clear_history"

AUTH_BASE_URL = "http://localhost:8000/auth"
GOOGLE_LOGIN_API = f"{AUTH_BASE_URL}/google/login"
GOOGLE_CALLBACK_API = f"{AUTH_BASE_URL}/google/callback"
WECHAT_QRCODE_API = f"{AUTH_BASE_URL}/wechat/qrcode"
WECHAT_CALLBACK_API = f"{AUTH_BASE_URL}/wechat/callback"

QR_CODE_TEMPLATE = "https://api.qrserver.com/v1/create-qr-code/?size=240x240&data={data}"
PROVIDER_LABELS = {"google": "Google", "wechat": "微信"}

st.set_page_config(page_title="DocChat AI - 智能文档问答", page_icon="📚", layout="wide")

# 添加基本的CSS样式确保文本换行
st.markdown(
    """
<style>
    /* 确保文本换行 */
    .stMarkdown, .stMarkdown * {
        word-wrap: break-word !important;
        word-break: break-word !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("📚 DocChat AI - 智能文档问答")

HISTORY_FILE = "data/chat_history.pkl"


# ================= 持久化工具函数 =================

def save_history_to_storage(history):
    """保存对话历史到持久化存储"""
    try:
        os.makedirs("data", exist_ok=True)
        with open(HISTORY_FILE, "wb") as f:
            pickle.dump(history, f)
        st.session_state["history"] = history
    except Exception as e:
        st.error(f"保存对话历史失败: {str(e)}")


def load_history_from_storage():
    """从持久化存储加载对话历史"""
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "rb") as f:
                return pickle.load(f)
    except Exception:
        pass
    return []


# ================= 登录辅助函数 =================

def _init_session_defaults():
    st.session_state.setdefault("oauth_pending_states", {})
    st.session_state.setdefault("wechat_login", None)


def remember_pending_state(state: str | None, provider: str, expires_in: int | float) -> None:
    if not state:
        return
    pending = st.session_state.setdefault("oauth_pending_states", {})
    pending[state] = {
        "provider": provider,
        "expires_at": time.time() + max(float(expires_in), 1.0),
    }


def cleanup_expired_oauth_states() -> None:
    pending = st.session_state.get("oauth_pending_states", {})
    now = time.time()
    expired_tokens = [token for token, meta in pending.items() if meta.get("expires_at", 0) <= now]
    for token in expired_tokens:
        pending.pop(token, None)


def trigger_external_redirect(url: str | None) -> None:
    if not url:
        st.error("登录地址缺失，请稍后重试。")
        return
    st.session_state["oauth_redirect_url"] = url
    st.rerun()


def start_google_login() -> None:
    try:
        response = requests.get(GOOGLE_LOGIN_API, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        st.error(f"获取 Google 登录链接失败：{exc}")
        return

    remember_pending_state(data.get("state"), "google", data.get("expires_in", 600))
    trigger_external_redirect(data.get("authorization_url"))


def ensure_wechat_login() -> dict | None:
    login_info = st.session_state.get("wechat_login")
    now = time.time()
    if login_info and login_info.get("expires_at", 0) - 5 > now:
        return login_info

    try:
        response = requests.get(WECHAT_QRCODE_API, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        st.error(f"获取微信二维码失败：{exc}")
        return None

    remember_pending_state(data.get("state"), "wechat", data.get("expires_in", 300))
    login_info = {
        "state": data.get("state"),
        "login_url": data.get("login_url"),
        "expires_at": now + float(data.get("expires_in", 300)),
    }
    st.session_state["wechat_login"] = login_info
    return login_info


def clear_oauth_query_params(params: dict[str, list[str]]) -> None:
    retained = {k: v for k, v in params.items() if k not in {"code", "state"}}
    st.query_params = retained


def _guess_provider_from_params(params: dict[str, list[str]]) -> str | None:
    if "scope" in params:
        return "google"
    return "wechat"


def handle_oauth_callback() -> None:
    params = st.query_params
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]

    if not code or not state:
        return

    pending = st.session_state.get("oauth_pending_states", {})
    entry = pending.pop(state, None)
    provider = entry.get("provider") if entry else _guess_provider_from_params(params)

    if provider not in {"google", "wechat"}:
        st.session_state["auth_feedback"] = ("warning", "登录状态已失效，请重新发起登录。")
        clear_oauth_query_params(params)
        st.rerun()

    callback_api = GOOGLE_CALLBACK_API if provider == "google" else WECHAT_CALLBACK_API
    try:
        response = requests.get(callback_api, params={"code": code, "state": state}, timeout=10)
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        st.session_state["auth_feedback"] = (
            "error",
            f"{PROVIDER_LABELS.get(provider, provider)} 登录失败：{detail}",
        )
    except requests.RequestException as exc:
        st.session_state["auth_feedback"] = (
            "error",
            f"{PROVIDER_LABELS.get(provider, provider)} 登录请求失败：{exc}",
        )
    else:
        st.session_state["auth_user"] = {
            "provider": provider,
            "profile": payload.get("profile", {}),
            "credentials": payload.get("credentials", {}),
            "logged_in_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        st.session_state["wechat_login"] = None
        st.session_state["auth_feedback"] = (
            "success",
            f"{PROVIDER_LABELS.get(provider, provider)} 登录成功。",
        )

    clear_oauth_query_params(params)
    st.rerun()


def logout_user() -> None:
    st.session_state.pop("auth_user", None)
    st.session_state["oauth_pending_states"] = {}
    st.session_state["wechat_login"] = None
    save_history_to_storage([])


def render_login_section() -> bool:
    st.subheader("🔐 账号登录")
    auth_user = st.session_state.get("auth_user")

    if auth_user:
        profile = auth_user.get("profile", {})
        provider = auth_user.get("provider")
        provider_label = PROVIDER_LABELS.get(provider, provider)

        col_main, col_avatar = st.columns([3, 1])
        with col_main:
            name = profile.get("name") or profile.get("nickname") or "未提供姓名"
            st.markdown(f"**已登录账号：** {name}")
            if profile.get("email"):
                st.markdown(f"- 邮箱：{profile['email']}")
            if profile.get("openid"):
                st.markdown(f"- OpenID：{profile['openid']}")
            st.markdown(f"- 登录方式：{provider_label}")
            st.caption(
                f"登录时间：{auth_user.get('logged_in_at', datetime.utcnow().isoformat(timespec='seconds'))}"
            )

            if st.button("退出登录", type="primary"):
                logout_user()
                st.rerun()

        with col_avatar:
            avatar_url = profile.get("picture") or profile.get("headimgurl")
            if avatar_url:
                st.image(avatar_url, width=100)

        st.divider()
        return True

    google_tab, wechat_tab = st.tabs(["Google 登录", "微信扫码登录"])
    with google_tab:
        st.write("使用 Google 账号进行登录，完成后将自动返回本页面。")
        if st.button("使用 Google 登录", type="primary"):
            start_google_login()

    with wechat_tab:
        st.write("使用个人微信扫码登录，二维码有效期有限，过期后请点击刷新。")
        login_info = ensure_wechat_login()
        if login_info and login_info.get("login_url"):
            encoded = quote_plus(login_info["login_url"])
            st.image(
                QR_CODE_TEMPLATE.format(data=encoded),
                caption="使用微信扫码完成登录",
            )
            remaining = max(int(login_info.get("expires_at", 0) - time.time()), 0)
            st.caption(f"二维码将在 {remaining} 秒后过期。")
            st.link_button("无法扫码？点击前往微信网页登录", login_info["login_url"])
        else:
            st.warning("暂时无法生成微信登录二维码，请稍后重试。")

        if st.button("刷新微信二维码"):
            st.session_state["wechat_login"] = None
            st.rerun()

    st.info("完成登录后即可继续使用 DocChat 的知识库与问答功能。")
    st.divider()
    return False


# ================= 页面初始化流程 =================

_init_session_defaults()

if st.session_state.get("oauth_redirect_url"):
    redirect_target = st.session_state.pop("oauth_redirect_url")
    st.markdown(
        f"<script>window.location.href = {json.dumps(redirect_target)};</script>",
        unsafe_allow_html=True,
    )
    st.stop()

cleanup_expired_oauth_states()
handle_oauth_callback()

feedback = st.session_state.pop("auth_feedback", None)
if feedback:
    level, message = feedback
    if level == "success":
        st.success(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.error(message)

if "history" not in st.session_state:
    st.session_state["history"] = load_history_from_storage()

authenticated = render_login_section()

if not authenticated:
    st.stop()

# ================= 侧边栏：知识库与清理操作 =================
with st.sidebar:
    st.header("📚 知识库文档")

    try:
        response = requests.get(LIST_DOCS_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            documents = data.get("documents", [])

            if documents:
                st.write(f"📄 当前知识库中有 {len(documents)} 个文档：")

                for doc in documents:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"• {doc['filename']} ({doc['size_mb']} MB)")
                    with col2:
                        if st.button("🗑️", key=f"delete_{doc['filename']}", help=f"删除 {doc['filename']}"):
                            try:
                                delete_response = requests.post(
                                    f"{DELETE_DOC_URL}/{doc['filename']}", timeout=10
                                )
                                if delete_response.status_code == 200:
                                    result = delete_response.json()
                                    st.success(f"{result['status']}: {result['message']}")
                                    st.rerun()
                                else:
                                    st.error(f"删除失败: {delete_response.status_code}")
                            except Exception as exc:
                                st.error(f"删除文档时发生错误: {exc}")
            else:
                st.info("📭 知识库为空，请上传PDF文档")
        else:
            st.error("获取文档列表失败")
    except Exception as exc:
        st.error(f"获取文档列表时发生错误: {exc}")

    st.divider()

    st.header("📂 上传PDF文档")
    files = st.file_uploader("上传文件", type=["pdf"], accept_multiple_files=True)
    if st.button("📘 构建知识库") and files:
        payload = []
        for file in files:
            try:
                encoded = base64.b64encode(file.read()).decode("utf-8")
                payload.append({"filename": file.name, "content": encoded})
            except Exception as exc:
                st.error(f"文件 {file.name} 编码失败: {exc}")
                continue

        if payload:
            try:
                resp = requests.post(UPLOAD_URL, json=payload, timeout=30)
            except requests.RequestException as exc:
                st.error(f"上传失败：{exc}")
            else:
                if resp.status_code == 200:
                    st.success(resp.json().get("status", "知识库已更新"))
                else:
                    st.error(f"上传失败: {resp.status_code}")
        else:
            st.error("没有有效的文件可以上传")

    st.divider()

    st.header("🧹 清理功能")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧹 清空记忆"):
            try:
                requests.post(RESET_URL, timeout=10)
                st.success("记忆已清空")
            except requests.RequestException as exc:
                st.error(f"清空记忆失败：{exc}")
    with col2:
        if st.button("🗑️ 清理对话历史"):
            try:
                response = requests.post(CLEAR_HISTORY_URL, timeout=10)
                if response.status_code == 200:
                    st.success("对话历史已清理")
                else:
                    st.error("清理对话历史失败")
            except requests.RequestException as exc:
                st.error(f"调用API失败: {exc}")
            save_history_to_storage([])
            st.rerun()

    st.divider()

    st.subheader("🗑️ 知识库管理")
    if st.button("🗂️ 清理知识库", type="secondary", help="删除所有上传的PDF文档和向量数据库"):
        try:
            response = requests.post(CLEAR_KB_URL, timeout=30)
            if response.status_code == 200:
                result = response.json()
                st.success(f"{result['status']}: {result['message']}")
                st.rerun()
            else:
                st.error(f"清理失败: {response.status_code}")
        except requests.RequestException as exc:
            st.error(f"清理知识库时发生错误: {exc}")

# ================= 对话主区域 =================
st.subheader("💬 对话区")
query = st.chat_input("请输入问题...")

for msg in st.session_state["history"]:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant"):
            st.markdown(msg["content"])


def process_sse_stream(buffer, data_buffer=""):
    """
    处理实时生成的 SSE 流式数据，确保有效数据不丢失，并保留换行符。
    :param buffer: 当前实时接收的数据片段
    :param data_buffer: 之前接收到的数据缓冲区，初始为空
    :return: 返回有效的解析数据列表，并更新data_buffer为剩余部分
    """
    data_buffer += buffer
    result = []
    is_done = False

    while True:
        start_index = data_buffer.find("data: ")
        end_index = data_buffer.find("data: DONE")

        if start_index == -1:
            break

        start_index += len("data: ")

        if end_index == -1:
            end_index = len(data_buffer) - 2

        valid_data = data_buffer[start_index:end_index]

        if valid_data:
            result.append(valid_data)

        data_buffer = data_buffer[end_index + 2 + len("data: DONE"):]

        if "data: DONE" in data_buffer:
            is_done = True
            break

    return result, data_buffer, is_done


if query:
    with st.chat_message("user"):
        st.markdown(query)

    st.session_state["history"].append({"role": "user", "content": query})
    save_history_to_storage(st.session_state["history"])

    full_response = ""
    try:
        response = requests.post(STREAM_API_URL, json={"query": query}, stream=True, timeout=30)

        if response.status_code == 200:
            with st.chat_message("assistant"):
                markdown_placeholder = st.empty()

                markdown_buffer = ""
                buffer = ""
                data_buffer = ""
                for chunk in response.iter_content(chunk_size=1024):
                    if not chunk:
                        continue

                    try:
                        buffer = chunk.decode("utf-8")
                    except UnicodeDecodeError:
                        buffer = chunk.decode("utf-8", errors="ignore")

                    results, data_buffer, is_done = process_sse_stream(buffer, data_buffer)

                    markdown_buffer = "".join(results)
                    full_response += markdown_buffer
                    markdown_placeholder.markdown(full_response)

                    if is_done:
                        break
        else:
            full_response = f"API请求失败，状态码：{response.status_code}"
            with st.chat_message("assistant"):
                st.markdown(full_response)

    except Exception as exc:
        full_response = f"抱歉，发生错误：{exc}"
        with st.chat_message("assistant"):
            st.markdown(full_response)

    if full_response and full_response.strip():
        st.session_state["history"].append({"role": "assistant", "content": full_response})
    else:
        default_response = "抱歉，未能生成有效响应，请重试。"
        st.session_state["history"].append({"role": "assistant", "content": default_response})

    save_history_to_storage(st.session_state["history"])
