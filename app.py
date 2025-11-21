import streamlit as st
import pandas as pd
import requests
from datetime import datetime, date
import json

# --- CẤU HÌNH ---
PAGE_TITLE = "Hệ thống Quản lý Dữ liệu Dân cư"
DEFAULT_PASSWORD = "NH11761321ieu@"

# Danh sách đầy đủ 40 cột
COLUMNS = [
    "TT", "Mã hộ", "Họ tên", "Giới tính", "Ngày sinh", "Số Căn cước", "Ngày cấp", "Nơi cấp", 
    "Dân tộc", "Số điện thoại", "Nơi đăng ký thường trú", "Nơi ở hiện tại", 
    "Thuộc hộ nghèo - cận nghèo", "Người khuyết tật", "Dân tộc thiểu số", 
    "Trình độ giáo dục phổ thông", "Trình độ chuyên môn kinh tế", "Lĩnh vực giáo dục đào tạo", 
    "Mã văn bằng", "Ngày cấp VB", "Đơn vị cấp VB", "Có việc làm", "Vị thế việc làm", 
    "Mã công việc đang làm", "Tên công việc đang làm", "Thuộc khu vực", "Tên nhóm ngành kinh tế", 
    "Nơi làm việc", "Địa chỉ nơi làm", "Địa chỉ chổ làm", "Loại hình kinh tế", "Thất nghiệp", 
    "Thời gian thất nghiệp", "Nhu cầu đào tạo", "Nhu cầu việc làm", 
    "Không tham gia hoạt động kinh tế", "Nguyên nhân không tham gia hoạt động kinh tế", 
    "Diễn giải công việc", "Ngày ghi", "Ngày cập nhật"
]

st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon="📋")

# --- HÀM XỬ LÝ ---

def check_password():
    """Trả về True nếu mật khẩu đúng"""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    st.markdown(f"## 🔒 Đăng nhập vào {PAGE_TITLE}")
    password = st.text_input("Nhập mật khẩu quản trị", type="password")
    
    if st.button("Đăng nhập"):
        if password == DEFAULT_PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Mật khẩu không đúng!")
    return False

def get_api_url():
    """Lấy URL API từ Session hoặc User Input"""
    if "GAS_URL" in st.secrets:
        return st.secrets["GAS_URL"]
    
    if "api_url" not in st.session_state:
        st.session_state.api_url = ""
    
    # Nút để reset URL nếu nhập sai
    if st.session_state.api_url:
        with st.sidebar:
            st.write(f"Đang kết nối tới: `{st.session_state.api_url[:30]}...`")
            if st.button("Đổi đường dẫn API"):
                st.session_state.api_url = ""
                st.rerun()

    if not st.session_state.api_url:
        st.info("Lần đầu truy cập, vui lòng nhập Google Apps Script Web App URL.")
        st.warning("LƯU Ý: Khi Deploy Apps Script, phần 'Who has access' BẮT BUỘC phải là 'Anyone'.")
        url = st.text_input("Dán URL Web App của bạn vào đây:", placeholder="https://script.google.com/macros/s/...")
        if st.button("Lưu cấu hình"):
            if url.startswith("https://script.google.com/"):
                st.session_state.api_url = url
                st.success("Đã lưu URL! Vui lòng đợi tải dữ liệu...")
                st.rerun()
            else:
                st.error("URL không hợp lệ.")
        return None
    return st.session_state.api_url

# Thêm cache để tăng tốc độ
@st.cache_data(ttl=60) 
def fetch_data(api_url):
    """Lấy dữ liệu từ Google Sheet và CHUẨN HÓA KIỂU DỮ LIỆU"""
    try:
        response = requests.get(api_url, params={"action": "read"})
        
        # --- KIỂM TRA LỖI KẾT NỐI ---
        if response.status_code != 200:
            st.error(f"❌ Lỗi kết nối tới Google Sheet! Mã lỗi HTTP: **{response.status_code}**")
            if response.status_code == 404:
                st.info("👉 Nguyên nhân: URL không tồn tại.")
            elif response.status_code in [401, 403]:
                st.info("👉 Nguyên nhân: Thiếu quyền truy cập (Chưa chọn 'Anyone').")
            return pd.DataFrame()

        try:
            data = response.json()
        except ValueError:
            st.error("❌ Dữ liệu trả về không phải JSON hợp lệ.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        
        if not df.empty:
            # 1. Chuyển cột TT sang số
            if "TT" in df.columns:
                df["TT"] = pd.to_numeric(df["TT"], errors='coerce')
            
            # 2. Xử lý cột Ngày & Giờ (Fix lỗi tz-aware vs tz-naive)
            # Chiến lược: Convert tất cả sang UTC (utc=True) để đồng bộ, 
            # sau đó xóa múi giờ (.dt.tz_localize(None)) để thành naive datetime.
            
            all_date_cols = ["Ngày sinh", "Ngày cấp", "Ngày cấp VB", "Ngày ghi", "Ngày cập nhật"]
            for col in all_date_cols:
                if col in df.columns:
                    # Ép kiểu sang datetime với utc=True để tránh lỗi mixed timezone
                    df[col] = pd.to_datetime(df[col], errors='coerce', utc=True)
                    # Xóa thông tin múi giờ để thành naive datetime (tương thích với st.data_editor)
                    df[col] = df[col].dt.tz_localize(None)

            # 3. Chuyển cột Text số (CCCD, SĐT) sang string tuyệt đối
            str_cols = ["Số Căn cước", "Số điện thoại", "Mã hộ", "Mã văn bằng", "Mã công việc đang làm"]
            for col in str_cols:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace(["nan", "None", "<NA>"], "")

        return df

    except Exception as e:
        st.error(f"❌ Lỗi ngoại lệ khi kết nối: {e}")
        return pd.DataFrame()

def send_data(api_url, data, action="add"):
    """Gửi dữ liệu (Thêm hoặc Sửa)"""
    payload = data
    payload['action'] = action
    try:
        with st.spinner('Đang xử lý dữ liệu...'):
            response = requests.post(api_url, json=payload)
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("status") == "success":
                    st.toast(res_json.get("message"), icon="✅")
                    fetch_data.clear()
                    return True
                else:
                    st.error(f"Lỗi từ Server: {res_json.get('message')}")
            else:
                st.error(f"Lỗi HTTP khi gửi dữ liệu: {response.status_code}")
    except Exception as e:
        st.error(f"Lỗi: {e}")
    return False

# --- GIAO DIỆN CHÍNH ---

if check_password():
    api_url = get_api_url()

    if api_url:
        st.title(f"📋 {PAGE_TITLE}")
        
        # Lấy dữ liệu
        df = fetch_data(api_url)
        
        tab1, tab2 = st.tabs(["📝 Nhập liệu mới", "Danh sách & Chỉnh sửa"])

        # --- TAB 1: FORM NHẬP LIỆU ---
        with tab1:
            st.markdown("### Nhập thông tin dân cư mới")
            
            # Tính toán số thứ tự tiếp theo
            if not df.empty and "TT" in df.columns:
                try:
                    current_max = df["TT"].max()
                    next_tt = 1 if pd.isna(current_max) else int(current_max) + 1
                except:
                    next_tt = len(df) + 1
            else:
                next_tt = 1

            with st.form("entry_form", clear_on_submit=False):
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Section 1: Định danh
                with st.expander("1. Thông tin định danh & Cá nhân", expanded=True):
                    c1, c2, c3, c4 = st.columns(4)
                    tt = c1.text_input("TT (Tự động)", value=str(next_tt), disabled=True)
                    ma_ho = c2.text_input("Mã hộ")
                    ho_ten = c3.text_input("Họ tên")
                    gioi_tinh = c4.selectbox("Giới tính", ["Nam", "Nữ", "Khác"])
                    
                    c5, c6, c7, c8 = st.columns(4)
                    ngay_sinh = c5.date_input("Ngày sinh", value=None, min_value=date(1900, 1, 1))
                    so_cccd = c6.text_input("Số Căn cước", max_chars=12, help="Nhập đủ 12 số")
                    ngay_cap = c7.date_input("Ngày cấp", value=None)
                    noi_cap = c8.text_input("Nơi cấp")
                    
                    c9, c10 = st.columns(2)
                    dan_toc = c9.text_input("Dân tộc", value="Kinh")
                    sdt = c10.text_input("Số điện thoại", max_chars=10, help="Nhập đủ 10 số")

                # Section 2: Cư trú & Xã hội
                with st.expander("2. Cư trú & Chính sách xã hội"):
                    thuong_tru = st.text_area("Nơi đăng ký thường trú", height=68)
                    hien_tai = st.text_area("Nơi ở hiện tại", height=68)
                    
                    xc1, xc2, xc3 = st.columns(3)
                    ho_ngheo = xc1.selectbox("Thuộc hộ nghèo/cận nghèo", ["Không", "Hộ nghèo", "Hộ cận nghèo"])
                    khuyet_tat = xc2.checkbox("Người khuyết tật")
                    dtts = xc3.checkbox("Dân tộc thiểu số")

                # Section 3: Học vấn
                with st.expander("3. Trình độ & Học vấn"):
                    hc1, hc2 = st.columns(2)
                    gdpt = hc1.selectbox("Trình độ GDPT", ["12/12", "9/12", "Tiểu học", "Mù chữ", "Khác"])
                    cmkt = hc2.text_input("Trình độ chuyên môn kinh tế")
                    
                    hc3, hc4 = st.columns(2)
                    linh_vuc = hc3.text_input("Lĩnh vực GD-ĐT")
                    ma_vb = hc4.text_input("Mã văn bằng")
                    
                    hc5, hc6 = st.columns(2)
                    ngay_cap_vb = hc5.date_input("Ngày cấp VB", value=None)
                    don_vi_cap = hc6.text_input("Đơn vị cấp VB")

                # Section 4: Việc làm
                with st.expander("4. Tình trạng Việc làm"):
                    vl1, vl2 = st.columns(2)
                    co_viec = vl1.selectbox("Có việc làm?", ["Có", "Không"])
                    vi_the = vl2.text_input("Vị thế việc làm")
                    
                    vl3, vl4 = st.columns(2)
                    ma_cv = vl3.text_input("Mã công việc đang làm")
                    ten_cv = vl4.text_input("Tên công việc đang làm")
                    
                    vl5, vl6 = st.columns(2)
                    khu_vuc = vl5.text_input("Thuộc khu vực")
                    nhom_nganh = vl6.text_input("Tên nhóm ngành kinh tế")
                    
                    vl7, vl8 = st.columns(2)
                    noi_lam = vl7.text_input("Nơi làm việc")
                    loai_hinh = vl8.text_input("Loại hình kinh tế")
                    
                    dc_lam = st.text_input("Địa chỉ nơi làm")
                    dc_cho_lam = st.text_input("Địa chỉ chổ làm (Cụ thể)")

                # Section 5: Thông tin khác
                with st.expander("5. Thông tin khác"):
                    k1, k2 = st.columns(2)
                    that_nghiep = k1.checkbox("Thất nghiệp")
                    tg_that_nghiep = k2.text_input("Thời gian thất nghiệp")
                    
                    k3, k4 = st.columns(2)
                    nhu_cau_dt = k3.text_input("Nhu cầu đào tạo")
                    nhu_cau_vl = k4.text_input("Nhu cầu việc làm")
                    
                    kt_kt = st.checkbox("Không tham gia hoạt động kinh tế")
                    nguyen_nhan_kt = st.text_input("Nguyên nhân không tham gia HĐKT")
                    dien_giai = st.text_area("Diễn giải công việc")

                # Nút submit
                submitted = st.form_submit_button("Lưu dữ liệu", type="primary")
                
                if submitted:
                    errors = []
                    if so_cccd and (len(so_cccd) != 12 or not so_cccd.isdigit()):
                        errors.append("⚠️ Số Căn cước phải bao gồm chính xác 12 chữ số.")
                    if sdt and (len(sdt) != 10 or not sdt.isdigit()):
                        errors.append("⚠️ Số điện thoại phải bao gồm chính xác 10 chữ số.")

                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        form_data = {
                            "TT": tt, "Mã hộ": ma_ho, "Họ tên": ho_ten, "Giới tính": gioi_tinh,
                            "Ngày sinh": str(ngay_sinh) if ngay_sinh else "",
                            "Số Căn cước": so_cccd,
                            "Ngày cấp": str(ngay_cap) if ngay_cap else "",
                            "Nơi cấp": noi_cap, "Dân tộc": dan_toc, "Số điện thoại": sdt,
                            "Nơi đăng ký thường trú": thuong_tru, "Nơi ở hiện tại": hien_tai,
                            "Thuộc hộ nghèo - cận nghèo": ho_ngheo,
                            "Người khuyết tật": "Có" if khuyet_tat else "Không",
                            "Dân tộc thiểu số": "Có" if dtts else "Không",
                            "Trình độ giáo dục phổ thông": gdpt, "Trình độ chuyên môn kinh tế": cmkt,
                            "Lĩnh vực giáo dục đào tạo": linh_vuc, "Mã văn bằng": ma_vb,
                            "Ngày cấp VB": str(ngay_cap_vb) if ngay_cap_vb else "",
                            "Đơn vị cấp VB": don_vi_cap, "Có việc làm": co_viec,
                            "Vị thế việc làm": vi_the, "Mã công việc đang làm": ma_cv,
                            "Tên công việc đang làm": ten_cv, "Thuộc khu vực": khu_vuc,
                            "Tên nhóm ngành kinh tế": nhom_nganh, "Nơi làm việc": noi_lam,
                            "Địa chỉ nơi làm": dc_lam, "Địa chỉ chổ làm": dc_cho_lam,
                            "Loại hình kinh tế": loai_hinh,
                            "Thất nghiệp": "Có" if that_nghiep else "Không",
                            "Thời gian thất nghiệp": tg_that_nghiep,
                            "Nhu cầu đào tạo": nhu_cau_dt, "Nhu cầu việc làm": nhu_cau_vl,
                            "Không tham gia hoạt động kinh tế": "Có" if kt_kt else "Không",
                            "Nguyên nhân không tham gia hoạt động kinh tế": nguyen_nhan_kt,
                            "Diễn giải công việc": dien_giai,
                            "Ngày ghi": now_str, "Ngày cập nhật": now_str
                        }
                        
                        if send_data(api_url, form_data, action="add"):
                            st.success("Đã thêm dữ liệu thành công!")
                            st.rerun()

        # --- TAB 2: XEM & SỬA DỮ LIỆU ---
        with tab2:
            st.markdown("### Cơ sở dữ liệu dân cư")
            if st.button("🔄 Tải lại dữ liệu"):
                fetch_data.clear()
                st.rerun()
            
            if not df.empty:
                display_cols = [c for c in df.columns if c != "_row_index"]
                
                column_config = {
                    "TT": st.column_config.NumberColumn("TT", format="%d"),
                    "Số Căn cước": st.column_config.TextColumn("Số Căn cước", help="12 chữ số", validate="^[0-9]{12}$"),
                    "Số điện thoại": st.column_config.TextColumn("Số điện thoại", help="10 chữ số", validate="^[0-9]{10}$"),
                    "Ngày sinh": st.column_config.DateColumn("Ngày sinh", format="DD/MM/YYYY"),
                    "Ngày cấp": st.column_config.DateColumn("Ngày cấp", format="DD/MM/YYYY"),
                    "Ngày cấp VB": st.column_config.DateColumn("Ngày cấp VB", format="DD/MM/YYYY"),
                    "Ngày ghi": st.column_config.DatetimeColumn("Ngày ghi", format="DD/MM/YYYY HH:mm", disabled=True),
                    "Ngày cập nhật": st.column_config.DatetimeColumn("Ngày cập nhật", format="DD/MM/YYYY HH:mm", disabled=True),
                }

                edited_df = st.data_editor(
                    df,
                    key="data_editor",
                    num_rows="dynamic",
                    column_order=display_cols,
                    column_config=column_config,
                    height=600
                )
                
                if st.button("Lưu các thay đổi đã chỉnh sửa", type="primary"):
                    changes = st.session_state["data_editor"]["edited_rows"]
                    added_rows = st.session_state["data_editor"]["added_rows"]
                    
                    progress_text = "Đang cập nhật dữ liệu..."
                    my_bar = st.progress(0, text=progress_text)
                    
                    total_changes = len(changes) + len(added_rows)
                    current_step = 0

                    # Xử lý Sửa (Update)
                    for idx, change_dict in changes.items():
                        row_index_in_sheet = df.iloc[int(idx)]["_row_index"]
                        
                        update_payload = change_dict.copy()
                        update_payload["_row_index"] = int(row_index_in_sheet)
                        update_payload["Ngày cập nhật"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        send_data(api_url, update_payload, action="update")
                        current_step += 1
                        my_bar.progress(current_step / total_changes if total_changes > 0 else 100, text=f"Đã cập nhật dòng {row_index_in_sheet}")

                    # Xử lý Thêm mới (Add) trực tiếp trên bảng
                    for new_row in added_rows:
                        try:
                            current_max = df["TT"].max()
                            next_tt = 1 if pd.isna(current_max) else int(current_max) + 1 + current_step
                        except:
                            next_tt = len(df) + 1 + current_step
                        
                        if "TT" not in new_row or not new_row["TT"]:
                            new_row["TT"] = next_tt
                            
                        new_row["Ngày ghi"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        new_row["Ngày cập nhật"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        send_data(api_url, new_row, action="add")
                        current_step += 1
                        my_bar.progress(current_step / total_changes, text="Đang thêm dòng mới...")

                    my_bar.empty()
                    if total_changes > 0:
                        st.success("Đã hoàn tất cập nhật!")
                        fetch_data.clear()
                        st.rerun()
                    else:
                        st.info("Không có thay đổi nào để lưu.")
            else:
                st.info("Chưa có dữ liệu. Vui lòng nhập liệu hoặc kiểm tra URL.")
