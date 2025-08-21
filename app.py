
import streamlit as st
import pandas as pd
from io import BytesIO
from pathlib import Path
import datetime

# ================== 설정 ==================
st.set_page_config(page_title="달구벌고등학교 기숙사 관리프로그램", layout="wide")
APP_TITLE_HTML = "<h3 style='margin:4px 0'>달구벌고등학교 기숙사 관리프로그램</h3>"
DATA_FILE = Path("data.xlsx")
ADMIN_ID = "admin"
ADMIN_PW = "admin123"

# 내부 저장 컬럼 (영문 컬럼으로 저장, 화면은 한글 표시)
STU_COLS = ["ID","Name","StudentNo","Gender","Room","Phone","ParentPhone","Address","MiddleSchool","InDate","OutDate","Password","Note"]
OUT_COLS = ["ID","StudentID","Type","Reason","StartDate","EndDate","Status"]
SCO_COLS = ["ID","StudentID","Category","Points","Reason","Date"]
PAY_COLS = ["ID","StudentID","Period","Amount","Status","PayDate","Method","Note"]

# ================== 공통 유틸 ==================
def _ensure_file():
    if not DATA_FILE.exists():
        with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as w:
            pd.DataFrame(columns=STU_COLS).to_excel(w, "Students", index=False)
            pd.DataFrame(columns=OUT_COLS).to_excel(w, "Outings", index=False)
            pd.DataFrame(columns=SCO_COLS).to_excel(w, "Scores", index=False)
            pd.DataFrame(columns=PAY_COLS).to_excel(w, "Payments", index=False)

def load_all():
    _ensure_file()
    xls = pd.ExcelFile(DATA_FILE, engine="openpyxl")
    students = pd.read_excel(xls, "Students").fillna("")
    outings  = pd.read_excel(xls, "Outings").fillna("")
    scores   = pd.read_excel(xls, "Scores").fillna("")
    payments = pd.read_excel(xls, "Payments").fillna("")
    return students, outings, scores, payments

def save_all(students, outings, scores, payments):
    with pd.ExcelWriter(DATA_FILE, engine="openpyxl") as w:  # 통합 저장 (append 모드 사용 안 함)
        students.to_excel(w, "Students", index=False)
        outings.to_excel(w,  "Outings", index=False)
        scores.to_excel(w,   "Scores", index=False)
        payments.to_excel(w, "Payments", index=False)

def next_id(df):
    if df.empty:
        return 1
    return int(pd.to_numeric(df["ID"], errors="coerce").max()) + 1

def name_by_sid(students, sid):
    row = students[students["ID"]==sid]
    return row.iloc[0]["Name"] if len(row)==1 else ""

def get_student_by_studentno(students, student_no):
    # 학번을 문자열로 비교
    return students[students["StudentNo"].astype(str) == str(student_no)]

# ================== 보고서 ==================
def make_report(students, outings, scores, payments):
    # 학생(한글 컬럼 추출)
    stu_export = students.rename(columns={
        "Name":"이름","StudentNo":"학번","Gender":"성별","Room":"호실",
        "Phone":"학생연락처","ParentPhone":"보호자연락처","Address":"주소",
        "MiddleSchool":"출신중학교","InDate":"입사일","OutDate":"퇴사일","Note":"특이사항"
    })[["이름","학번","성별","호실","학생연락처","보호자연락처","주소","출신중학교","입사일","퇴사일","특이사항"]]

    # 외출_외박
    out = outings.copy()
    out["이름"] = out["StudentID"].apply(lambda x: name_by_sid(students, x))
    out_export = out.rename(columns={"Type":"구분","Reason":"사유","StartDate":"시작일","EndDate":"종료일","Status":"상태"})
    out_export = out_export[["이름","구분","사유","시작일","종료일","상태"]]

    # 상벌점
    sco = scores.copy()
    sco["이름"] = sco["StudentID"].apply(lambda x: name_by_sid(students, x))
    sco_export = sco.rename(columns={"Category":"구분","Points":"점수","Reason":"사유_비고","Date":"일자"})
    sco_export = sco_export[["이름","구분","점수","사유_비고","일자"]]

    # 납부
    pay = payments.copy()
    pay["이름"] = pay["StudentID"].apply(lambda x: name_by_sid(students, x))
    pay_export = pay.rename(columns={"Period":"납부_회차_기간","Amount":"금액","Status":"상태","PayDate":"납부일","Method":"방법","Note":"비고"})
    pay_export = pay_export[["이름","납부_회차_기간","금액","상태","납부일","방법","비고"]]

    # 상벌점 요약
    if len(sco_export)==0:
        summary = pd.DataFrame(columns=["이름","총 상점","총 벌점","순점수"])
    else:
        pos = sco_export[sco_export["점수"]>0].groupby("이름")["점수"].sum().rename("총 상점")
        neg = sco_export[sco_export["점수"]<0].groupby("이름")["점수"].sum().rename("총 벌점")
        net = sco_export.groupby("이름")["점수"].sum().rename("순점수")
        summary = pd.concat([pos,neg,net], axis=1).fillna(0).reset_index()

    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as w:
        stu_export.to_excel(w, "학생", index=False)
        out_export.to_excel(w, "외출_외박", index=False)
        sco_export.to_excel(w, "상벌점", index=False)
        pay_export.to_excel(w, "납부", index=False)
        summary.to_excel(w, "상벌점_요약", index=False)
    return bio.getvalue()

# ================== 로그인 로직 ==================
def login_admin(uid, pw):
    return uid == ADMIN_ID and pw == ADMIN_PW

def login_student(student_no, pw):
    students, *_ = load_all()
    m = get_student_by_studentno(students, student_no)
    if len(m)==1 and str(m.iloc[0]["Password"]) == str(pw):
        return True, int(m.iloc[0]["ID"])
    return False, None

# ================== UI 렌더러 ==================
def render_header():
    st.markdown(APP_TITLE_HTML, unsafe_allow_html=True)

def render_logout():
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.session_state.refresh = True

# ================== 관리자 화면 ==================
def admin_screen():
    render_header()
    st.sidebar.markdown("**관리자 대시보드**")
    render_logout()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["학생관리","외출·외박","상벌점","납부","보고서 다운로드"])

    # ---- 학생관리 ----
    with tab1:
        st.subheader("학생관리 (등록/수정/삭제)")
        students, outings, scores, payments = load_all()
        with st.form("add_stu", clear_on_submit=True):
            c1,c2,c3 = st.columns(3)
            with c1:
                name = st.text_input("이름")
                gender = st.radio("성별", ["남","여"], horizontal=True)
                stu_no = st.text_input("학번")
                pw = st.text_input("비밀번호", type="password")
            with c2:
                room = st.text_input("호실")
                phone = st.text_input("학생연락처")
                pphone = st.text_input("보호자연락처")
                address = st.text_area("주소")
            with c3:
                middle = st.text_input("출신중학교")
                in_date = st.date_input("입사일", datetime.date.today())
                out_date_en = st.checkbox("퇴사일 입력")
                out_date = st.date_input("퇴사일", datetime.date.today()) if out_date_en else ""
                note = st.text_area("특이사항")
            sub = st.form_submit_button("등록")
            if sub:
                if not (name and stu_no and pw):
                    st.error("이름/학번/비밀번호는 필수입니다.")
                elif (students["StudentNo"].astype(str) == str(stu_no)).any():
                    st.error("이미 존재하는 학번입니다.")
                else:
                    new = {"ID": next_id(students),"Name":name,"StudentNo":str(stu_no),"Gender":gender,
                           "Room":room,"Phone":phone,"ParentPhone":pphone,"Address":address,
                           "MiddleSchool":middle,"InDate":in_date.isoformat(),
                           "OutDate": out_date if isinstance(out_date,str) else out_date.isoformat(),
                           "Password":pw,"Note":note}
                    students = pd.concat([students, pd.DataFrame([new])], ignore_index=True)
                    save_all(students, outings, scores, payments)
                    st.success("학생 등록 완료")
                    st.session_state.refresh = True

        # 학생 목록(한글 헤더)
        students_view = students.rename(columns={
            "Name":"이름","StudentNo":"학번","Gender":"성별","Room":"호실",
            "Phone":"학생연락처","ParentPhone":"보호자연락처","Address":"주소",
            "MiddleSchool":"출신중학교","InDate":"입사일","OutDate":"퇴사일","Note":"특이사항"
        })
        students_view = students_view[["ID","이름","학번","성별","호실","학생연락처","보호자연락처","주소","출신중학교","입사일","퇴사일","특이사항"]] if len(students_view) else students_view
        st.markdown("### 학생 목록")
        st.dataframe(students_view, use_container_width=True)

        st.markdown("### 학생 수정/삭제")
        stu_no_list = students["StudentNo"].astype(str).tolist() if len(students) else []
        sel = st.selectbox("수정/삭제할 학번 선택", stu_no_list) if stu_no_list else None
        if sel:
            selected_df = get_student_by_studentno(students, sel)
            if not selected_df.empty:
                row = selected_df.iloc[0]
                with st.form("edit_stu"):
                    c1,c2,c3 = st.columns(3)
                    with c1:
                        name_e = st.text_input("이름", row["Name"])
                        gender_e = st.radio("성별", ["남","여"], index=0 if row["Gender"]=="남" else 1, horizontal=True)
                        stu_no_e = st.text_input("학번", str(row["StudentNo"]))
                    with c2:
                        room_e = st.text_input("호실", row["Room"])
                        phone_e = st.text_input("학생연락처", row["Phone"])
                        pphone_e = st.text_input("보호자연락처", row["ParentPhone"])
                    with c3:
                        address_e = st.text_area("주소", row["Address"])
                        middle_e = st.text_input("출신중학교", row["MiddleSchool"])
                        in_e = st.date_input("입사일", datetime.date.fromisoformat(row["InDate"]) if row["InDate"] else datetime.date.today())
                        out_e = st.date_input("퇴사일", datetime.date.fromisoformat(row["OutDate"]) if row["OutDate"] else datetime.date.today())
                    note_e = st.text_area("특이사항", row["Note"])
                    pw_e = st.text_input("비밀번호(변경 시 입력)", value="", type="password")
                    c1b,c2b = st.columns(2)
                    with c1b:
                        upd = st.form_submit_button("수정 저장")
                    with c2b:
                        del_related = st.checkbox("관련 기록도 삭제(외출·외박/상벌점/납부)")
                        dele = st.form_submit_button("학생 삭제")

                    if upd:
                        idx = students.index[get_student_by_studentno(students, row["StudentNo"]).index][0]
                        students.loc[idx, ["Name","StudentNo","Gender","Room","Phone","ParentPhone",
                                           "Address","MiddleSchool","InDate","OutDate","Note"]] = [
                            name_e, str(stu_no_e), gender_e, room_e, phone_e, pphone_e, address_e, middle_e,
                            in_e.isoformat(), out_e.isoformat(), note_e
                        ]
                        if pw_e:
                            students.loc[idx,"Password"] = pw_e
                        # 학번이 바뀌면 연관 데이터의 StudentID는 그대로 (ID 매칭) 이므로 영향 없음
                        save_all(students, outings, scores, payments)
                        st.success("수정 완료")
                        st.session_state.refresh = True

                    if dele:
                        sid = int(row["ID"])
                        students = students[students["ID"]!=sid].copy()
                        if del_related:
                            outings = outings[outings["StudentID"]!=sid].copy()
                            scores = scores[scores["StudentID"]!=sid].copy()
                            payments = payments[payments["StudentID"]!=sid].copy()
                        save_all(students, outings, scores, payments)
                        st.warning("삭제 완료")
                        st.session_state.refresh = True
            else:
                st.warning("선택한 학번을 찾을 수 없습니다.")

    # ---- 외출·외박 ----
    with tab2:
        st.subheader("외출·외박 관리")
        students, outings, scores, payments = load_all()
        if len(students)==0:
            st.info("학생을 먼저 등록하세요.")
        else:
            with st.form("add_outing"):
                sid = st.selectbox("학생 선택", students["ID"].tolist(), format_func=lambda x: name_by_sid(students, x))
                otype = st.radio("구분", ["외출","외박"], horizontal=True)
                reason = st.text_area("사유")
                c1,c2 = st.columns(2)
                with c1: s = st.date_input("시작일", datetime.date.today())
                with c2: e = st.date_input("종료일", datetime.date.today())
                status = st.selectbox("상태", ["신청","대기","승인","반려","취소"])
                sub = st.form_submit_button("등록")
                if sub:
                    new = {"ID": next_id(outings),"StudentID": int(sid),"Type": otype,"Reason": reason,
                           "StartDate": s.isoformat(),"EndDate": e.isoformat(),"Status": status}
                    outings = pd.concat([outings, pd.DataFrame([new])], ignore_index=True)
                    save_all(students, outings, scores, payments)
                    st.success("저장 완료")
                    st.session_state.refresh = True

        if len(outings):
            view = outings.copy()
            view["이름"] = view["StudentID"].apply(lambda x: name_by_sid(students, x))
            view = view.rename(columns={"Type":"구분","Reason":"사유","StartDate":"시작일","EndDate":"종료일","Status":"상태"})
            view = view[["ID","이름","구분","사유","시작일","종료일","상태"]]
            st.dataframe(view, use_container_width=True)

    # ---- 상벌점 ----
    with tab3:
        st.subheader("상벌점 관리")
        students, outings, scores, payments = load_all()
        if len(students)==0:
            st.info("학생을 먼저 등록하세요.")
        else:
            with st.form("add_score"):
                sid = st.selectbox("학생 선택", students["ID"].tolist(), format_func=lambda x: name_by_sid(students, x))
                category = st.radio("구분", ["상점","벌점"], horizontal=True)
                pts = st.number_input("점수", value=1, step=1)
                reason = st.text_area("사유/비고")
                d = st.date_input("일자", datetime.date.today())
                sub = st.form_submit_button("등록")
                if sub:
                    p = int(pts if category=="상점" else -abs(pts))
                    new = {"ID": next_id(scores),"StudentID": int(sid),"Category": category,
                           "Points": p,"Reason": reason,"Date": d.isoformat()}
                    scores = pd.concat([scores, pd.DataFrame([new])], ignore_index=True)
                    save_all(students, outings, scores, payments)
                    st.success("저장 완료")
                    st.session_state.refresh = True

        if len(scores):
            view = scores.copy()
            view["이름"] = view["StudentID"].apply(lambda x: name_by_sid(students, x))
            view = view.rename(columns={"Category":"구분","Points":"점수","Reason":"사유_비고","Date":"일자"})
            view = view[["ID","이름","구분","점수","사유_비고","일자"]]
            st.dataframe(view, use_container_width=True)

    # ---- 납부 ----
    with tab4:
        st.subheader("기숙사비 납부 관리")
        students, outings, scores, payments = load_all()
        if len(students)==0:
            st.info("학생을 먼저 등록하세요.")
        else:
            with st.form("add_pay"):
                sid = st.selectbox("학생 선택", students["ID"].tolist(), format_func=lambda x: name_by_sid(students, x))
                period = st.text_input("납부 회차/기간")
                amount = st.number_input("금액", min_value=0, step=10000)
                status = st.radio("상태", ["납부","미납"], horizontal=True)
                pay_date = st.date_input("납부일", datetime.date.today())
                method = st.selectbox("방법", ["현금","카드","이체","기타"])
                note = st.text_area("비고")
                sub = st.form_submit_button("등록")
                if sub:
                    new = {"ID": next_id(payments),"StudentID": int(sid),"Period": period,
                           "Amount": int(amount),"Status": status,"PayDate": pay_date.isoformat(),
                           "Method": method,"Note": note}
                    payments = pd.concat([payments, pd.DataFrame([new])], ignore_index=True)
                    save_all(students, outings, scores, payments)
                    st.success("저장 완료")
                    st.session_state.refresh = True

        if len(payments):
            view = payments.copy()
            view["이름"] = view["StudentID"].apply(lambda x: name_by_sid(students, x))
            view = view.rename(columns={"Period":"납부_회차_기간","Amount":"금액","Status":"상태","PayDate":"납부일","Method":"방법","Note":"비고"})
            view = view[["ID","이름","납부_회차_기간","금액","상태","납부일","방법","비고"]]
            st.dataframe(view, use_container_width=True)

    # ---- 보고서 ----
    with tab5:
        st.subheader("엑셀 보고서 다운로드")
        students, outings, scores, payments = load_all()
        data = make_report(students, outings, scores, payments)
        st.download_button("📥 보고서 다운로드", data, file_name="report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ================== 학생 화면 ==================
def student_screen(sid:int):
    render_header()
    students, outings, scores, payments = load_all()
    myname = name_by_sid(students, sid) or "학생"
    st.sidebar.markdown(f"**학생 대시보드: {myname}**")
    render_logout()

    tab1, tab2, tab3 = st.tabs(["외출·외박 신청/취소","나의 상벌점","나의 납부 내역"])

    # 외출·외박 신청/취소
    with tab1:
        st.subheader("외출·외박 신청")
        with st.form("req_out"):
            otype = st.radio("구분", ["외출","외박"], horizontal=True)
            reason = st.text_area("사유")
            c1,c2 = st.columns(2)
            with c1: s = st.date_input("시작일", datetime.date.today())
            with c2: e = st.date_input("종료일", datetime.date.today())
            sub = st.form_submit_button("신청")
            if sub:
                new = {"ID": next_id(outings),"StudentID": int(sid),"Type": otype,"Reason": reason,
                       "StartDate": s.isoformat(),"EndDate": e.isoformat(),"Status": "신청"}
                outings = pd.concat([outings, pd.DataFrame([new])], ignore_index=True)
                save_all(students, outings, scores, payments)
                st.success("신청 완료")
                st.session_state.refresh = True

        mine = outings[outings["StudentID"]==sid].copy().sort_values("ID", ascending=False)
        st.markdown("### 내 신청 내역")
        if len(mine):
            view = mine.rename(columns={"Type":"구분","Reason":"사유","StartDate":"시작일","EndDate":"종료일","Status":"상태"})
            view = view[["ID","구분","사유","시작일","종료일","상태"]]
            st.dataframe(view, use_container_width=True)

            pend = mine[mine["Status"].isin(["신청","대기"])]
            if len(pend):
                labels = [f"{int(r.ID)} | {r.Type} {r.StartDate}~{r.EndDate} | {r.Status}" for _, r in pend.iterrows()]
                sel = st.selectbox("취소할 신청 선택 (ID | 유형 기간 | 상태)", labels) if len(labels) else None
                if st.button("신청 취소"):
                    if sel:
                        cancel_id = int(sel.split("|")[0].strip())
                        idxs = outings.index[outings["ID"]==cancel_id].tolist()
                        if idxs:
                            outings.loc[idxs[0],"Status"] = "취소"
                            save_all(students, outings, scores, payments)
                            st.success("취소되었습니다.")
                            st.session_state.refresh = True
            else:
                st.info("취소 가능한(신청/대기) 내역이 없습니다.")
        else:
            st.info("신청 내역이 없습니다.")

    # 나의 상벌점
    with tab2:
        st.subheader("나의 상벌점 조회")
        mine = scores[scores["StudentID"]==sid].copy().sort_values("ID", ascending=False)
        if len(mine):
            view = mine.rename(columns={"Category":"구분","Points":"점수","Reason":"사유_비고","Date":"일자"})
            view = view[["구분","점수","사유_비고","일자"]]
            st.dataframe(view, use_container_width=True)
            pos = mine[mine["Points"]>0]["Points"].sum()
            neg = mine[mine["Points"]<0]["Points"].sum()
            st.write(f"총 상점: **{int(pos)}**점 | 총 벌점: **{int(neg)}**점 | 순점수: **{int(mine['Points'].sum())}**점")
        else:
            st.info("상벌점 기록이 없습니다.")

    # 나의 납부 내역
    with tab3:
        st.subheader("나의 납부 내역")
        mine = payments[payments["StudentID"]==sid].copy().sort_values("ID", ascending=False)
        if len(mine):
            view = mine.rename(columns={"Period":"납부_회차_기간","Amount":"금액","Status":"상태","PayDate":"납부일","Method":"방법","Note":"비고"})
            view = view[["납부_회차_기간","금액","상태","납부일","방법","비고"]]
            st.dataframe(view, use_container_width=True)
        else:
            st.info("납부 기록이 없습니다.")

# ================== 엔트리 ==================
if "role" not in st.session_state:
    st.session_state.role = None
if "sid" not in st.session_state:
    st.session_state.sid = None
if "refresh" not in st.session_state:
    st.session_state.refresh = False

if st.session_state.role is None:
    render_header()
    st.subheader("로그인")
    who = st.radio("사용자 유형", ["관리자","학생"], horizontal=True)
    uid = st.text_input("ID (관리자는 admin / 학생은 학번)")
    pw = st.text_input("비밀번호", type="password")
    login = st.button("로그인")
    if login:
        if who == "관리자":
            if login_admin(uid, pw):
                st.session_state.role = "admin"
                st.session_state.refresh = True
            else:
                st.error("관리자 로그인 실패")
        else:
            ok, sid = login_student(uid, pw)
            if ok:
                st.session_state.role = "student"
                st.session_state.sid = sid
                st.session_state.refresh = True
            else:
                st.error("학생 로그인 실패: 학번 또는 비밀번호를 확인하세요.")

    if st.session_state.refresh:
        st.session_state.refresh = False
        st.rerun()
    st.stop()

# 라우팅
if st.session_state.role == "admin":
    admin_screen()
elif st.session_state.role == "student":
    student_screen(int(st.session_state.sid))

# 최종 refresh 처리
if st.session_state.get("refresh", False):
    st.session_state["refresh"] = False
    st.rerun()
