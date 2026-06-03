import streamlit as st
import pandas as pd

# ตั้งค่าหน้าเว็บให้แสดงผลเต็มจอกว้างๆ
st.set_page_config(page_title="AVATR EA Simulation", layout="wide")

st.title("📊 AVATR EA Simulation Dashboard")
st.caption("ระบบจำลองคำนวณแผนออกไม้แบบ Grid / Martingale 3 Phases ตามเงื่อนไข AVATR")
st.markdown("---")

# ================= SIDEBAR INPUTS =================
st.sidebar.header("🔧 พารามิเตอร์หลัก (Inputs)")

# ส่วนที่ 1: ข้อมูลพอร์ตและการออกไม้แรก
balance_cent = st.sidebar.number_input("ยอดเงิน Balance (Cent)", min_value=100, value=249855, step=1000)
start_lot = st.sidebar.number_input("Start Lot (ไม้ที่ 1)", min_value=0.01, value=0.04, step=0.01, format="%.2f")
start_price = st.sidebar.number_input("ราคาไม้แรก (Position)", min_value=0.0, value=4477.0, step=10.0)
direction = st.sidebar.selectbox("ฝั่งการเทรด (Direction)", ["SELL (ลากขึ้นเกิด DD)", "BUY (ลากลงเกิด DD)"])

st.sidebar.markdown("---")
st.sidebar.header("⚙️ ปรับสเต็ปและเฟสการออกออเดอร์")

# Phase 1
st.sidebar.subheader("Phase 1 (ไม้ที่ 1 - 4)")
p1_orders = st.sidebar.number_input("จำนวนไม้ P1", min_value=1, value=4)
p1_mult = st.sidebar.number_input("ตัวคูณ P1 (Mult)", min_value=1.0, value=1.8, step=0.1)
p1_step = st.sidebar.number_input("ระยะห่าง P1 (จุด)", min_value=10, value=150)

# Phase 2
st.sidebar.subheader("Phase 2")
p2_orders = st.sidebar.number_input("จำนวนไม้ P2", min_value=1, value=7)
p2_mult = st.sidebar.number_input("ตัวคูณ P2 (Mult)", min_value=1.0, value=1.4, step=0.1)
p2_step = st.sidebar.number_input("ระยะห่าง P2 (จุด)", min_value=10, value=150)

# Phase 3
st.sidebar.subheader("Phase 3 (จนกว่าพอร์ตแตก)")
p3_mult = st.sidebar.number_input("ตัวคูณ P3 (Mult)", min_value=1.0, value=2.0, step=0.1)
p3_step = st.sidebar.number_input("ระยะห่าง P3 (จุด)", min_value=10, value=1500)

# ================= LOGIC CALCULATION =================
records = []
total_lots_accumulated = 0
total_distance_accumulated = 0
total_cost_product = 0

for order_no in range(1, 21):
    # จัดเฟสอ้างอิงตามค่าอินพุตจริง
    if order_no <= p1_orders:
        phase_name = f"Phase 1" if order_no > 1 else "-"
        multiplier = p1_mult if order_no > 1 else 1.0
        step = p1_step
    elif order_no <= (p1_orders + p2_orders):
        phase_name = f"Phase 2"
        multiplier = p2_mult
        step = p2_step
    else:
        phase_name = f"Phase 3"
        multiplier = p3_mult
        step = p3_step
        
    # คำนวณ Lot ดิบ และ Lot แท้จริง (ตรรกะคูณต่อจาก Lot แท้จริงก่อนหน้าแล้วปัดลงทศนิยม 2 ตำแหน่ง)
    if order_no == 1:
        lot_raw = start_lot
        lot_actual = start_lot
    else:
        lot_raw = records[-1]['LOT แท้จริง'] * multiplier
        # ตรรกะปัดทศนิยม 2 ตำแหน่งแบบไม่ปัดขึ้น (Truncate/Floor เพื่อให้ได้ 1.13, 2.25, 4.50 ตรงกับรูป)
        lot_actual = int(lot_raw * 100) / 100.0
        
    # คำนวณระยะสะสมและราคาเปิดไม้
    if order_no == 1:
        current_price = start_price
        distance_step = 0
    else:
        distance_step = step
        if "SELL" in direction:
            current_price += distance_step
        else:
            current_price -= distance_step
            
    total_distance_accumulated += distance_step
    total_lots_accumulated += lot_actual
    
    # คำนวณจุดเสมอทุนสะสม (Break-Even Price)
    total_cost_product += (lot_actual * current_price)
    be_price = round(total_cost_product / total_lots_accumulated, 2)
    
    # คำนวณ Floating Loss สะสม ณ ระดับราคาปัจจุบันของไม้นั้นๆ
    floating_loss_cent = 0
    for i in range(len(records)):
        prev_open = records[i]['ราคาเปิดออเดอร์']
        prev_lot = records[i]['LOT แท้จริง']
        if "SELL" in direction:
            diff = current_price - prev_open
        else:
            diff = prev_open - current_price
        floating_loss_cent += (diff * prev_lot)
        
    dd_percent = (floating_loss_cent / balance_cent) * 100
    
    # คำนวณระยะต้องวกกลับ (Trailing) เพื่อปิดกำไรเสมอทุน
    if "SELL" in direction:
        distance_to_be = round(current_price - be_price)
    else:
        distance_to_be = round(be_price - current_price)
        
    records.append({
        'ไม้': order_no,
        'เฟส': phase_name,
        'ตัวคูณ': f"{multiplier}x" if order_no > 1 else "-",
        'LOT ดิบ': round(lot_raw, 4),
        'LOT แท้จริง': lot_actual,
        'ระยะสะสม': total_distance_accumulated,
        'ราคาเปิดออเดอร์': current_price,
        'ราคาเฉลี่ย (BE)': be_price,
        'ต้องวกกลับ': distance_to_be,
        'FLOATING LOSS': round(floating_loss_cent, 2),
        'DRAWDOWN': round(dd_percent, 2)
    })

df = pd.DataFrame(records)

# ================= DISPLAY TOP CARDS =================
total_lots_top = round(df['LOT แท้จริง'].sum(), 2)
final_loss_top = df.iloc[-1]['FLOATING LOSS']
final_dd_top = df.iloc[-1]['DRAWDOWN']

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="LOTS สะสมทั้งหมด (20 ไม้)", value=f"{total_lots_top} Lots")
with col2:
    st.metric(label="FLOATING LOSS สูงสุด (Cent)", value=f"{final_loss_top:,.2f} Cent")
with col3:
    st.metric(label="🔴 DRAWDOWN สูงสุดที่ไม้ 20", value=f"{final_dd_top:.2f}%")

st.markdown("---")

# ================= DISPLAY TABLE =================
st.subheader("📋 ตาราง Simulation แสดงผลลัพธ์ไม้ที่ 1 - 20")

formatted_df = df.copy()
formatted_df['LOT ดิบ'] = formatted_df['LOT ดิบ'].map('{:,.4f}'.format)
formatted_df['LOT แท้จริง'] = formatted_df['LOT แท้จริง'].map('{:,.2f}'.format)
formatted_df['ระยะสะสม'] = formatted_df['ระยะสะสม'].map('{:,.0f}'.format)
formatted_df['ราคาเปิดออเดอร์'] = formatted_df['ราคาเปิดออเดอร์'].map('{:,.2f}'.format)
formatted_df['ราคาเฉลี่ย (BE)'] = formatted_df['ราคาเฉลี่ย (BE)'].map('{:,.2f}'.format)
formatted_df['ต้องวกกลับ'] = formatted_df['ต้องวกกลับ'].map('{:,.0f}'.format)
formatted_df['FLOATING LOSS'] = formatted_df['FLOATING LOSS'].map('{:,.2f}'.format)
formatted_df['DRAWDOWN'] = formatted_df['DRAWDOWN'].map('{:,.2f}%'.format)

# สไตล์การจัดหน้าตารางให้แสดงผลสวยงามและอ่านง่าย
st.dataframe(formatted_df, use_container_width=True, hide_index=True)
