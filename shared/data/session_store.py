"""
shared/data/session_store.py

시뮬레이션 세션 저장/불러오기 (SQLite)

결정 로그 D-008, D-013:
  - 단독 세션 사용 시 st.session_state로 충분하나
    저장/불러오기 기능 필요 시 SQLite 도입
  - JSON 직렬화로 모든 결과 저장 (중첩 딕셔너리, DataFrame 포함)

사용법:
  store = SessionStore()
  session_id = store.save(name="삼성전자_시나리오A", data=result_dict)
  result = store.load(session_id)
  sessions = store.list_sessions()
  store.delete(session_id)
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import Any


DB_PATH = Path(".cache/sessions.db")


class SessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id          TEXT PRIMARY KEY,
                    name        TEXT NOT NULL,
                    section     TEXT NOT NULL,
                    country     TEXT,
                    industry    TEXT,
                    company     TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    notes       TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created
                ON sessions (created_at DESC)
            """)
            conn.commit()

    def save(
        self,
        name: str,
        data: dict,
        section: str = "both",
        country: str = None,
        industry: str = None,
        company: str = None,
        notes: str = None,
        session_id: str = None,
    ) -> str:
        """
        시뮬레이션 결과 저장. session_id 지정 시 업데이트, 없으면 신규 생성.
        반환값: session_id
        """
        now = datetime.now().isoformat()
        sid = session_id or str(uuid.uuid4())[:8]

        serialized = self._serialize(data)

        with sqlite3.connect(self.db_path) as conn:
            if session_id:
                conn.execute("""
                    UPDATE sessions
                    SET name=?, section=?, country=?, industry=?, company=?,
                        updated_at=?, data=?, notes=?
                    WHERE id=?
                """, (name, section, country, industry, company,
                      now, serialized, notes, sid))
            else:
                conn.execute("""
                    INSERT INTO sessions
                    (id, name, section, country, industry, company,
                     created_at, updated_at, data, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sid, name, section, country, industry, company,
                      now, now, serialized, notes))
            conn.commit()

        return sid

    def load(self, session_id: str) -> dict | None:
        """세션 ID로 결과 불러오기. 없으면 None 반환."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM sessions WHERE id=?", (session_id,)
            ).fetchone()

        if not row:
            return None

        result = dict(row)
        result["data"] = self._deserialize(result["data"])
        return result

    def list_sessions(
        self,
        section: str = None,
        country: str = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        저장된 세션 목록 반환 (최신순).
        section, country 필터 옵션.
        """
        query = "SELECT id, name, section, country, industry, company, created_at, notes FROM sessions"
        conditions, params = [], []

        if section:
            conditions.append("section=?")
            params.append(section)
        if country:
            conditions.append("country=?")
            params.append(country)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [dict(r) for r in rows]

    def delete(self, session_id: str) -> bool:
        """세션 삭제. 성공 여부 반환."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE id=?", (session_id,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def export_json(self, session_id: str, path: Path) -> bool:
        """세션을 JSON 파일로 내보내기."""
        session = self.load(session_id)
        if not session:
            return False
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2, default=str)
        return True

    def import_json(self, path: Path) -> str | None:
        """JSON 파일에서 세션 가져오기. 새 session_id로 저장."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                session = json.load(f)
            return self.save(
                name=session.get("name", "imported"),
                data=session.get("data", {}),
                section=session.get("section", "both"),
                country=session.get("country"),
                industry=session.get("industry"),
                company=session.get("company"),
                notes=f"imported from {path.name}",
            )
        except Exception:
            return None

    def _serialize(self, data: Any) -> str:
        """딕셔너리/DataFrame 포함 데이터를 JSON 문자열로 변환."""
        return json.dumps(data, ensure_ascii=False, default=self._json_default)

    def _deserialize(self, text: str) -> Any:
        """JSON 문자열 → Python 객체. DataFrame 복원 포함."""
        raw = json.loads(text)
        return self._restore_dataframes(raw)

    @staticmethod
    def _json_default(obj):
        if isinstance(obj, pd.DataFrame):
            return {"__type__": "DataFrame", "data": obj.to_dict(orient="records")}
        if isinstance(obj, pd.Series):
            return {"__type__": "Series", "data": obj.to_dict()}
        if hasattr(obj, "__float__"):
            return float(obj)
        if hasattr(obj, "__int__"):
            return int(obj)
        return str(obj)

    @staticmethod
    def _restore_dataframes(obj: Any) -> Any:
        if isinstance(obj, dict):
            if obj.get("__type__") == "DataFrame":
                return pd.DataFrame(obj["data"])
            if obj.get("__type__") == "Series":
                return pd.Series(obj["data"])
            return {k: SessionStore._restore_dataframes(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [SessionStore._restore_dataframes(i) for i in obj]
        return obj


# ── Streamlit UI 헬퍼 ──────────────────────────────────────────────

def render_session_panel(store: SessionStore):
    """
    Streamlit 사이드바 또는 탭에 삽입할 세션 관리 패널.
    st.session_state["current_session_id"] 를 통해 앱과 연동.

    사용법:
      import streamlit as st
      from shared.data.session_store import SessionStore, render_session_panel
      store = SessionStore()
      render_session_panel(store)
    """
    try:
        import streamlit as st
    except ImportError:
        return

    st.markdown("### 세션 관리")

    sessions = store.list_sessions(limit=20)

    if sessions:
        options = {f"[{s['id']}] {s['name']} ({s['created_at'][:10]})": s["id"]
                   for s in sessions}
        selected_label = st.selectbox("저장된 세션 불러오기", ["-- 선택 --"] + list(options.keys()))

        if selected_label != "-- 선택 --":
            sid = options[selected_label]
            col1, col2 = st.columns(2)
            with col1:
                if st.button("불러오기", use_container_width=True):
                    session = store.load(sid)
                    if session:
                        st.session_state["loaded_session"] = session["data"]
                        st.session_state["current_session_id"] = sid
                        st.success(f"세션 '{session['name']}' 불러왔습니다.")
                        st.rerun()
            with col2:
                if st.button("삭제", use_container_width=True):
                    store.delete(sid)
                    st.warning("삭제되었습니다.")
                    st.rerun()
    else:
        st.caption("저장된 세션이 없습니다.")

    st.divider()

    with st.expander("현재 세션 저장"):
        save_name = st.text_input("세션 이름", placeholder="예: 삼성전자_공격적_시나리오")
        save_notes = st.text_area("메모 (선택)", height=60)
        if st.button("저장", use_container_width=True):
            if save_name and st.session_state.get("simulation_result"):
                meta = st.session_state.get("context_meta", {})
                sid = store.save(
                    name=save_name,
                    data=st.session_state["simulation_result"],
                    country=meta.get("country"),
                    industry=meta.get("industry"),
                    company=meta.get("company"),
                    notes=save_notes,
                    session_id=st.session_state.get("current_session_id"),
                )
                st.session_state["current_session_id"] = sid
                st.success(f"저장 완료 (ID: {sid})")
            elif not save_name:
                st.error("세션 이름을 입력해주세요.")
            else:
                st.warning("시뮬레이션 결과가 없습니다. 먼저 시뮬레이션을 실행하세요.")
